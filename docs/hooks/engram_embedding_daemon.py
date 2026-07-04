"""engram-embedding-daemon — multilingual pre-warmed semantic recall service.

Cycle #59 → #60 (2026-05-14).

This is the SEMANTIC RECALL daemon used by the UserPromptSubmit hook.
It is INTENTIONALLY DECOUPLED from engram.embedding (which production
hippo_* tools use): the daemon loads a SEPARATE encoder optimised for
the proactive-recall use-case (multilingual IT/EN), without forcing a
migration on the main facts.embedding column.

Encoder choice (cycle #60): `paraphrase-multilingual-MiniLM-L12-v2`
(384 dim, ~480 MB on disk, already cached from previous downloads).
Empirically chosen because:
  - paraphrase-multilingual covers 50+ langs incl. Italian properly
  - dim 384 = same memory footprint as the production MiniLM-L6
  - sentence-transformers SOTA tier for cross-lingual retrieval
  - cold load ~5-8s (vs 15s for MiniLM-L6-v2 first-load — already in cache)

Since the facts in semantic.db are encoded with the LEGACY MiniLM-L6
(production encoder), we cannot dot-product their stored blobs against
the new encoder's output. So the daemon maintains its OWN in-memory
cache of (fact_id, proposition_vector_in_new_space). Lazy refresh on
each request: any new facts not in cache are encoded on the fly.

Protocol v2 (single RPC, server-side cosine):
  REQ:  {"prompt": "...",
         "top_k": 3,
         "threshold": 0.50,
         "excluded_ids": ["id1", "id2"]}
  RESP: {"hits": [
            {"id", "proposition", "topic", "similarity", "created_at"}
          ],
          "n_total_facts": 421,
          "encode_ms": 12.3,
          "match_ms": 1.1,
          "encoder": "paraphrase-multilingual-MiniLM-L12-v2"}
  ERR:  {"error": "..."}

Lifecycle unchanged from cycle #59: spawn detached, publish daemon.json,
exit after 30 min idle. Hook does PID-check before connecting.
"""
from __future__ import annotations

import atexit
import json
import os
import signal
import socket
import sqlite3
import sys
import threading
import time
from pathlib import Path

DAEMON_JSON_PATH = Path.home() / ".engram" / "daemon.json"
IDLE_TIMEOUT_S = 30 * 60  # 30 min

# Cycle #60: encoder = local cached HF model. Resolved by sentence-transformers
# to the on-disk cache when offline env vars are set.
ENCODER_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


# Shared state for idle tracking
_last_request_ts = time.time()
_lock = threading.Lock()


def _set_idle_now() -> None:
    global _last_request_ts
    with _lock:
        _last_request_ts = time.time()


def _idle_seconds() -> float:
    with _lock:
        return time.time() - _last_request_ts


def _publish(pid: int, port: int) -> None:
    DAEMON_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    DAEMON_JSON_PATH.write_text(
        json.dumps({
            "pid": pid, "port": port,
            "host": "127.0.0.1",
            "started_at": time.time(),
            "protocol_version": 2,  # cycle #60: server-side cosine
            "encoder": ENCODER_MODEL,
        }),
        encoding="utf-8",
    )


def _unpublish() -> None:
    try:
        DAEMON_JSON_PATH.unlink()
    except FileNotFoundError:
        pass


# ---------- Facts cache --------------------------------------------------


class FactsCache:
    """In-memory cache of fact vectors encoded with the new encoder.
    Lazy refresh: any fact id present in semantic.db but not in cache
    gets encoded on the next refresh() call. Removed-from-DB ids get
    purged from cache. Thread-safe: a single lock around the whole
    refresh+search."""

    def __init__(self, encoder, sem_db_path: Path) -> None:
        import numpy as np  # noqa
        self.encoder = encoder
        self.sem_db = sem_db_path
        self.ids: list[str] = []
        self.props: list[str] = []
        self.topics: list[str] = []
        self.created_ats: list[float] = []
        self.vectors = None  # np.ndarray (N, dim) or None
        self._lock = threading.Lock()

    def refresh(self) -> dict:
        """Sync cache with semantic.db. Returns stats dict."""
        import numpy as np
        t0 = time.perf_counter()
        # Codex tribunal finding (3-LLM verified 2026-05-28): `with
        # sqlite3.connect() as conn` commits but does NOT close the
        # connection — the fd/handle lingers until GC. Severity LOW on
        # CPython (refcount GC closes it at scope exit), but on Windows
        # (strict file locking) / PyPy a lingering read connection can
        # block unlink and interfere with WAL checkpoint. Explicit close
        # + busy_timeout for safety on a shared WAL db.
        conn = sqlite3.connect(str(self.sem_db), timeout=60.0)
        try:
            conn.execute("PRAGMA busy_timeout=60000;")
            rows = conn.execute(
                "SELECT id, proposition, topic, created_at FROM facts"
            ).fetchall()
        finally:
            conn.close()
        db_ids = [r[0] for r in rows]
        db_id_set = set(db_ids)

        with self._lock:
            existing = {fid: i for i, fid in enumerate(self.ids)}
            removed = set(self.ids) - db_id_set
            new_rows = [r for r in rows if r[0] not in existing]

            # Apply removals first (rebuild filtered)
            if removed:
                keep_idx = [
                    i for i, fid in enumerate(self.ids)
                    if fid not in removed
                ]
                self.ids = [self.ids[i] for i in keep_idx]
                self.props = [self.props[i] for i in keep_idx]
                self.topics = [self.topics[i] for i in keep_idx]
                self.created_ats = [
                    self.created_ats[i] for i in keep_idx
                ]
                if self.vectors is not None and len(keep_idx) > 0:
                    self.vectors = self.vectors[keep_idx]
                elif self.vectors is not None:
                    self.vectors = None

            # Append new rows (batch encode for speed)
            if new_rows:
                new_props = [r[1] or "" for r in new_rows]
                # Batch encode in chunks to bound memory.
                CHUNK = 64
                new_vecs_list = []
                for i in range(0, len(new_props), CHUNK):
                    batch = new_props[i:i + CHUNK]
                    arr = self.encoder(batch)
                    new_vecs_list.append(arr)
                new_vecs = np.vstack(new_vecs_list).astype(
                    np.float32, copy=False
                )
                for r in new_rows:
                    self.ids.append(r[0])
                    self.props.append(r[1] or "")
                    self.topics.append(r[2] or "")
                    try:
                        self.created_ats.append(float(r[3] or time.time()))
                    except (TypeError, ValueError):
                        self.created_ats.append(time.time())
                if self.vectors is None:
                    self.vectors = new_vecs
                else:
                    self.vectors = np.vstack([self.vectors, new_vecs])

        return {
            "n_total": len(self.ids),
            "n_added": len(new_rows),
            "n_removed": len(removed),
            "refresh_ms": round((time.perf_counter() - t0) * 1000.0, 1),
        }

    def search(
        self, query_text: str, *,
        top_k: int = 3, threshold: float = 0.5,
        excluded_ids: set[str] | None = None,
    ) -> tuple[list[dict], float, float]:
        import numpy as np
        excluded_ids = excluded_ids or set()
        with self._lock:
            if not self.ids or self.vectors is None:
                return [], 0.0, 0.0
            # Snapshot refs (cheap, no copy)
            ids = list(self.ids)
            props = list(self.props)
            topics = list(self.topics)
            ats = list(self.created_ats)
            V = self.vectors

        t0 = time.perf_counter()
        q = self.encoder([query_text])[0].astype(np.float32, copy=False)
        # encoder is normalize_embeddings=True so q is unit-norm.
        encode_ms = (time.perf_counter() - t0) * 1000.0

        t1 = time.perf_counter()
        sims = V @ q  # (N,)
        # Argsort desc
        order = np.argsort(-sims)
        hits: list[dict] = []
        for i in order:
            fid = ids[i]
            if fid in excluded_ids:
                continue
            sim = float(sims[i])
            if sim < threshold:
                # Since order is desc, we can break.
                break
            hits.append({
                "id": fid,
                "proposition": props[i],
                "topic": topics[i],
                "similarity": round(sim, 4),
                "created_at": ats[i],
            })
            if len(hits) >= top_k:
                break
        match_ms = (time.perf_counter() - t1) * 1000.0
        return hits, encode_ms, match_ms


# ---------- Network handlers --------------------------------------------


def _handle_client(conn: socket.socket, cache: FactsCache) -> None:
    try:
        conn.settimeout(5.0)
        buf = b""
        while b"\n" not in buf:
            chunk = conn.recv(65536)
            if not chunk:
                break
            buf += chunk
            if len(buf) > 1_000_000:
                break
        line = buf.split(b"\n", 1)[0].decode("utf-8", errors="replace")
        try:
            req = json.loads(line)
        except Exception as exc:
            conn.sendall(
                (json.dumps({"error": f"bad json: {exc}"}) + "\n").encode()
            )
            return

        prompt = (req.get("prompt") or "").strip()
        if not prompt:
            conn.sendall(
                (json.dumps({"error": "empty prompt"}) + "\n").encode()
            )
            return

        try:
            top_k = max(1, min(int(req.get("top_k", 3)), 20))
        except (TypeError, ValueError):
            top_k = 3
        try:
            threshold = max(0.0, min(float(req.get("threshold", 0.5)), 1.0))
        except (TypeError, ValueError):
            threshold = 0.5
        excluded_ids = set(req.get("excluded_ids") or [])

        # Refresh cache (lazy: pulls in new/removed facts since last)
        stats = cache.refresh()
        hits, encode_ms, match_ms = cache.search(
            prompt, top_k=top_k, threshold=threshold,
            excluded_ids=excluded_ids,
        )

        resp = {
            "hits": hits,
            "n_total_facts": stats["n_total"],
            "refresh": stats,
            "encode_ms": round(encode_ms, 2),
            "match_ms": round(match_ms, 2),
            "encoder": ENCODER_MODEL,
            "protocol_version": 2,
        }
        conn.sendall((json.dumps(resp, ensure_ascii=False) + "\n").encode("utf-8"))
        _set_idle_now()
    except TimeoutError:
        pass
    except Exception as exc:
        try:
            conn.sendall(
                (json.dumps({"error": f"server: {type(exc).__name__}: {exc}"})
                 + "\n").encode()
            )
        except Exception:
            pass
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _idle_watchdog(stop_event: threading.Event) -> None:
    while not stop_event.wait(60.0):
        if _idle_seconds() > IDLE_TIMEOUT_S:
            os.kill(os.getpid(), signal.SIGTERM)
            return


def _build_encoder():
    """Load the multilingual encoder. Pure sentence-transformers, no
    dependency on engram.embedding (which still uses MiniLM-L6 for
    production paths)."""
    os.environ.setdefault("HIPPO_OFFLINE", "1")
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(ENCODER_MODEL)

    def encode(texts):
        """texts: str or list[str]. Returns np.ndarray L2-normalized."""
        import numpy as np
        single = isinstance(texts, str)
        if single:
            texts = [texts]
        arr = model.encode(
            texts, normalize_embeddings=True,
            show_progress_bar=False, convert_to_numpy=True,
        )
        arr = arr.astype(np.float32, copy=False)
        return arr[0] if single else arr

    return encode


def main() -> int:
    os.environ.setdefault("HIPPO_DATA_DIR", str(Path.home() / ".engram"))
    os.environ.setdefault("ENGRAM_DATA_DIR", str(Path.home() / ".engram"))

    print(f"loading encoder: {ENCODER_MODEL} ...", flush=True)
    t0 = time.time()
    encoder = _build_encoder()
    # Warm-up
    _ = encoder("warmup")
    print(f"encoder ready in {time.time()-t0:.1f}s", flush=True)

    # Locate semantic.db
    data_dir = Path(os.environ["ENGRAM_DATA_DIR"])
    sem_db = data_dir / "semantic" / "semantic.db"
    if not sem_db.exists():
        sem_db = data_dir / "semantic.db"
    if not sem_db.exists():
        print(f"FATAL: semantic.db not found under {data_dir}", flush=True)
        return 1

    cache = FactsCache(encoder, sem_db)
    # Build initial cache eagerly (so the first hook request is fast)
    print("building facts cache ...", flush=True)
    t1 = time.time()
    init_stats = cache.refresh()
    print(
        f"cache built: {init_stats['n_total']} facts in "
        f"{init_stats['refresh_ms']:.0f}ms "
        f"(total wall {time.time()-t1:.1f}s)",
        flush=True,
    )

    # Open listening socket.
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", 0))
    sock.listen(8)
    host, port = sock.getsockname()

    pid = os.getpid()
    _publish(pid, port)
    atexit.register(_unpublish)
    print(f"engram-embedding-daemon listening on {host}:{port} pid={pid}",
          flush=True)

    stop = threading.Event()
    watchdog = threading.Thread(
        target=_idle_watchdog, args=(stop,), daemon=True,
    )
    watchdog.start()

    def _shutdown(*_args):
        stop.set()
        try:
            sock.close()
        except Exception:
            pass
        _unpublish()
        sys.exit(0)

    signal.signal(signal.SIGTERM, _shutdown)
    try:
        signal.signal(signal.SIGINT, _shutdown)
    except Exception:
        pass

    try:
        while True:
            try:
                conn, _addr = sock.accept()
            except OSError:
                break
            t = threading.Thread(
                target=_handle_client, args=(conn, cache), daemon=True,
            )
            t.start()
    finally:
        _shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
