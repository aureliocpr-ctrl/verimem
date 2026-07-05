"""Local sentence embedding (sentence-transformers).

Cosine similarity utilities. Embeddings are float32 numpy arrays, L2-normalized
on encode so dot product = cosine similarity.

Single-text encodings are LRU-cached (see encode_cache_*) — the agent
re-encodes the same task / skill / fact text many times within a single
sleep cycle or wake loop, and `sentence-transformers.encode` is the most
expensive step in the pipeline (~5-15 ms per call on CPU).
"""
from __future__ import annotations

import os
import threading
from collections.abc import Iterable
from functools import lru_cache

import numpy as np

from .config import CONFIG

# Cache size — 1024 unique texts is a safe ceiling for skill triggers,
# task summaries, and recently-recalled fact propositions. Each entry is
# 384 floats × 4 bytes ≈ 1.5 KB → 1.5 MB at full saturation.
_ENCODE_CACHE_SIZE = 1024


_MODEL = None
_MODEL_LOCK = threading.Lock()
# Max seconds to wait for the model-load lock. Longer than a legit cold load
# (~20s) but BOUNDED: a wedged loader must NEVER block callers forever (the
# 2026-06-05 4h save/recall hang). Env-overridable.
_MODEL_LOCK_TIMEOUT_S = float(os.environ.get("ENGRAM_MODEL_LOCK_TIMEOUT_S") or 90)

_OFFLINE_ENV_VARS = ("HIPPO_OFFLINE", "ENGRAM_OFFLINE", "HF_HUB_OFFLINE",
                     "TRANSFORMERS_OFFLINE")


def _offline() -> bool:
    """True if any offline flag forbids network model loads (the production
    MCP config). A network model load is then both wrong AND the cause of the
    2026-06-05 hang — a stall under _MODEL_LOCK wedges all embedding for hours."""
    truthy = {"1", "true", "yes", "on"}
    return any(
        os.environ.get(v, "").strip().lower() in truthy
        for v in _OFFLINE_ENV_VARS
    )


def _load_model():
    from sentence_transformers import SentenceTransformer

    model = CONFIG.embedding_model
    try:
        # Cache-only: evita il round-trip di rete a HF Hub ad OGNI load (il check
        # "unauthenticated HF Hub" — lento/flaky offline o sotto rate-limit, puo'
        # stallare il PRIMO encode di un server MCP a freddo: hang osservato su
        # recall/write via MCP). Verificato 2026-06-04: con local_files_only il
        # warning di rete sparisce. Fallback al load CON rete solo se il modello
        # non e' ancora in cache (primo download).
        return SentenceTransformer(model, local_files_only=True)
    except Exception:  # noqa: BLE001
        # 2026-06-05 ROOT-CAUSE FIX (4h save/recall hang): the network fallback
        # can stall indefinitely on a flaky / rate-limited HF Hub, and it runs
        # under _MODEL_LOCK -> a stall wedges EVERY embedding for hours. NEVER
        # touch the network when an offline flag is set (the production config);
        # re-raise so the caller fails fast. The network path is only a genuine
        # first-download in an explicitly-online setup.
        if _offline():
            raise
        return SentenceTransformer(model)


def _model():
    """Return the process-wide SentenceTransformer, loading it exactly once.

    Double-checked locking: a background preload thread (engram.preload) can
    race the first real request; without the lock both would pay the ~20s
    cold load, because functools.lru_cache does NOT serialise concurrent
    misses (it only locks the cache bookkeeping, not the wrapped call).
    """
    global _MODEL
    if _MODEL is None:
        # 2026-06-05: BOUNDED lock wait. A wedged loader (e.g. a stalled model
        # load that held the lock) must not block callers forever — raise after
        # the timeout instead (degraded-but-responsive > the 4h infinite hang).
        if not _MODEL_LOCK.acquire(timeout=_MODEL_LOCK_TIMEOUT_S):
            raise RuntimeError(
                "embedding model load timed out waiting on _MODEL_LOCK "
                f"({_MODEL_LOCK_TIMEOUT_S}s) — a loader is wedged; failing fast"
            )
        try:
            if _MODEL is None:
                _MODEL = _load_model()
                _adopt_true_dim(_MODEL)
        finally:
            _MODEL_LOCK.release()
    return _MODEL


def _adopt_true_dim(model) -> None:
    """iter 31 — kill the silent-empty-recall trap: when CONFIG.embedding_dim is
    an ASSUMPTION (unknown model, no pinned HIPPO_EMBEDDING_DIM), adopt the
    loaded model's true dimension. The recall length-filter reads
    CONFIG.embedding_dim per access, so the late update takes effect for every
    subsequent store/recall. A pinned or known-table dim is never overridden.
    Best-effort: any error leaves the assumption in place (warned at config)."""
    try:
        from engram.config import CONFIG
        if not getattr(CONFIG, "embedding_dim_assumed", False):
            return
        dim = model.get_sentence_embedding_dimension()
        if dim and int(dim) != CONFIG.embedding_dim:
            import logging
            logging.getLogger(__name__).warning(
                "embedding_dim auto-detected %d -> %d from loaded model "
                "(was an assumption for an unknown model)",
                CONFIG.embedding_dim, int(dim))
        if dim:
            object.__setattr__(CONFIG, "embedding_dim", int(dim))
            object.__setattr__(CONFIG, "embedding_dim_assumed", False)
    except Exception:  # noqa: BLE001 — adoption must never break model load
        pass


def is_loaded() -> bool:
    """True if the in-process model is already resident — PURE, never loads it.

    A no-side-effect readiness probe so callers (warmup-status tool, health
    gates) can tell whether a semantic call will be warm or pay the ~20s cold
    cliff, without themselves triggering that load.
    """
    return _MODEL is not None


def _reset_model_for_tests() -> None:
    """Test-only: drop the cached model and the single-text encode cache."""
    global _MODEL
    with _MODEL_LOCK:
        _MODEL = None
    _cached_encode.cache_clear()


# --- Shared encode service (engram.encode_service) -------------------------
# Many processes (N MCP servers + every fresh `clp` invocation) otherwise each
# load their own ~500 MB model and pay the ~20s cold start. encode() tries a
# shared warm service first and falls back to in-process on ANY miss/error, so
# the service is a pure optimisation, never a hard dependency.
_SERVICE_CONNECT_TIMEOUT_S = 0.5
_SERVICE_READ_TIMEOUT_S = 5.0


class EncodeDelegateUnavailable(RuntimeError):
    """Raised by encode() in DELEGATE-ONLY mode when the shared encode daemon is
    unavailable AND the in-process model is not already warm — so the caller must
    DEGRADE (recall→keyword, save→defer) instead of paying the ~33s
    `import sentence_transformers` + model load UNDER _MODEL_LOCK, which blocks
    every concurrent recall/save (the recurring hang; hang-trace 2026-06-06)."""


_DELEGATE_ONLY_TRUTHY = {"1", "true", "yes", "on"}


def _delegate_only() -> bool:
    """True in an MCP-server process (``HIPPO_ENCODE_DELEGATE_ONLY=1``): NEVER
    cold-load the model here — only the shared daemon loads it (once). Read at
    call time so it stays env-/test-controllable. The daemon + CLI leave it
    unset, so they still load in-process normally."""
    return (
        os.environ.get("HIPPO_ENCODE_DELEGATE_ONLY", "").strip().lower()
        in _DELEGATE_ONLY_TRUTHY
    )


def _encode_local(text: str) -> np.ndarray:
    """In-process encode (loads the model once). Never touches the service —
    the encode service itself calls this, so it must not recurse."""
    model = _model()
    vec = model.encode(text, normalize_embeddings=True, show_progress_bar=False)
    return np.asarray(vec, dtype=np.float32)


def _encode_via_service(text: str) -> np.ndarray | None:
    """Encode via the shared service. Returns None if unavailable so the
    caller falls back to in-process encoding."""
    if os.environ.get("ENGRAM_ENCODE_SERVICE", "1").strip().lower() in (
        "0", "false", "no", "off",
    ):
        return None
    try:
        import socket as _socket

        from . import encode_service as _svc

        info = _svc.read_discovery()
        if not info or not info.get("port"):
            return None
        # rescan2 fix 2026-06-02 (NONNA): usa il daemon SOLO se serve lo STESSO
        # modello di CONFIG. Un daemon stale/di altra config produce vettori in
        # uno spazio embedding diverso (stessa dim -> passa il filtro byte ma
        # cosine non comparabile = poisoning silenzioso del corpus). Mismatch o
        # 'model' assente -> None -> fallback al local encode (modello corretto).
        if info.get("model") != CONFIG.embedding_model:
            return None
        conn = _socket.create_connection(
            (info.get("host", "127.0.0.1"), info["port"]),
            timeout=_SERVICE_CONNECT_TIMEOUT_S,
        )
        try:
            conn.settimeout(_SERVICE_READ_TIMEOUT_S)
            _svc.send_msg(conn, {"text": text})
            resp = _svc.recv_msg(conn)
        finally:
            conn.close()
        if resp and resp.get("ok") and "vec" in resp:
            return np.asarray(resp["vec"], dtype=np.float32)
    except Exception:  # noqa: BLE001 — any failure → fall back to local encode
        return None
    return None


def _encode_one(text: str) -> np.ndarray:
    """Single-text encode: shared service first, in-process fallback.

    DELEGATE-ONLY (MCP server): refuse the in-process COLD-load (raise
    EncodeDelegateUnavailable) so the caller degrades instead of blocking ~33s
    under _MODEL_LOCK — but still use an already-warm in-process model if one
    happens to be loaded (no cold-load = no lock contention)."""
    vec = _encode_via_service(text)
    if vec is not None:
        return vec
    if _delegate_only() and not is_loaded():
        raise EncodeDelegateUnavailable(
            "encode daemon unavailable and in-process cold-load is disabled "
            "(HIPPO_ENCODE_DELEGATE_ONLY=1) — caller must degrade"
        )
    return _encode_local(text)


@lru_cache(maxsize=_ENCODE_CACHE_SIZE)
def _cached_encode(text: str) -> bytes:
    """LRU-cached single-text encode. Returns bytes for hashable storage."""
    return _encode_one(text).tobytes()


def encode(text: str | Iterable[str]) -> np.ndarray:
    """Encode text(s) to L2-normalized float32 vectors.

    Returns shape (D,) for single string, (N, D) for iterable.
    Single-text encodings hit a 1024-entry LRU cache.

    DELEGATE-ONLY (audit#2 2026-06-08, A-2): the batch branch used to call
    ``_model()`` directly, cold-loading the model under ``_MODEL_LOCK`` (~33s)
    even when ``HIPPO_ENCODE_DELEGATE_ONLY=1`` forbids it — the exact hang the
    single-text path guards against, reached via ``record_episodes_batch`` on an
    MCP server. It now mirrors the single-text contract: with no warm model in
    delegate-only mode it encodes per-text through the shared service (LRU-
    cached) and raises ``EncodeDelegateUnavailable`` if the daemon is down, so
    the caller DEGRADES instead of wedging every concurrent recall/save.
    """
    if isinstance(text, str):
        return np.frombuffer(_cached_encode(text), dtype=np.float32)
    texts = list(text)
    if not texts:
        # Nothing to encode — never cold-load just to return an empty matrix.
        return np.empty((0, CONFIG.embedding_dim), dtype=np.float32)
    if _delegate_only() and not is_loaded():
        # No in-process cold-load here. Route each text through the cached
        # single-text path (service-first; raises EncodeDelegateUnavailable if
        # the daemon is unavailable — same DEGRADE contract as the str branch).
        return np.stack(
            [np.frombuffer(_cached_encode(t), dtype=np.float32) for t in texts]
        )
    # Warm in-process model, or cold-load permitted (daemon / CLI process):
    # true batch encode — ~10x the per-text path (SIMD + amortized overhead).
    model = _model()
    arr = model.encode(
        texts, normalize_embeddings=True, show_progress_bar=False, convert_to_numpy=True
    )
    return arr.astype(np.float32, copy=False)


def encode_cache_clear() -> None:
    """Drop all cached single-text embeddings.

    Call when swapping the embedding model at runtime (rare).
    """
    _cached_encode.cache_clear()


def encode_cache_info() -> object:
    """Return functools.lru_cache CacheInfo (hits, misses, maxsize, currsize)."""
    return _cached_encode.cache_info()


# --- Embedding-model versioning primitives (2026-06-03, additive) ----------
# Identity of the active encoder. These are the building blocks a future
# per-row ``embedding_model`` column (and a model-aware recall filter) will
# use to avoid same-dim cross-space poisoning. Pure reads of CONFIG — no
# behaviour change, no model load (except verify_model_dim, which is explicit).


def model_signature() -> str:
    """Version tag of the active encoder (``CONFIG.embedding_model``).

    Intended as the value stamped on a per-row ``embedding_model`` column so
    recall can later filter to vectors produced by the current encoder.
    """
    return CONFIG.embedding_model


def _needs_e5_prefix() -> bool:
    """e5 models (intfloat/*e5*) sono addestrati coi prefissi ``query: ``/``passage: ``;
    gli altri (MiniLM, paraphrase-multilingual) NON li usano. Gate sul nome del modello
    attivo: cambia comportamento SOLO per un e5 -> backward-compat zero per L12/MiniLM."""
    return "e5" in CONFIG.embedding_model.lower()


def as_query(text: str) -> str:
    """Testo come QUERY per il modello attivo: e5 -> ``query: ``+text; altri -> invariato.
    Usare a RECALL-time sulla query di ricerca (asimmetria query/passage di e5)."""
    return f"query: {text}" if _needs_e5_prefix() else text


def as_passage(text: str) -> str:
    """Testo come PASSAGE per il modello attivo: e5 -> ``passage: ``+text; altri -> invariato.
    Usare a STORE/re-embed time sul testo memorizzato (proposition/summary/trigger/turn)."""
    return f"passage: {text}" if _needs_e5_prefix() else text


def expected_embedding_bytes() -> int:
    """Serialized byte length of one embedding for the active model.

    ``CONFIG.embedding_dim * 4`` (float32). This is the SINGLE source of the
    recall byte-filter: ``semantic._EXPECTED_EMBEDDING_BYTES`` resolves to this
    LIVE on every access (PEP 562 ``__getattr__``, harden 2026-06-07), so a
    runtime embedding-dim change updates the facts/episodes/skills length-guard
    instead of leaving it frozen at the import-time dim.
    """
    return CONFIG.embedding_dim * 4


def verify_model_dim() -> tuple[bool, int]:
    """Falsification guard: load the encoder and compare its real output dim
    to ``CONFIG.embedding_dim``.

    Returns ``(matches, actual_dim)``. LOADS the model (explicit, never at
    import) — call it from a migration prestep before re-embedding, to fail
    closed on a dim mismatch instead of writing wrong-length vectors.
    """
    model = _model()
    getter = getattr(model, "get_sentence_embedding_dimension", None)
    if callable(getter):
        actual = int(getter())
    else:  # defensive: derive from a probe encode
        actual = int(np.asarray(_encode_local("dim probe")).shape[-1])
    return (actual == CONFIG.embedding_dim, actual)


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two L2-normalized vectors."""
    return float(np.dot(a, b))


def cosine_matrix(query: np.ndarray, corpus: np.ndarray) -> np.ndarray:
    """Cosine similarity of one query vector against a (N, D) corpus matrix."""
    if corpus.ndim == 1:
        return np.array([cosine(query, corpus)])
    return corpus @ query


def serialize(vec: np.ndarray) -> bytes:
    return np.ascontiguousarray(vec, dtype=np.float32).tobytes()


def deserialize(blob: bytes) -> np.ndarray:
    return np.frombuffer(blob, dtype=np.float32)
