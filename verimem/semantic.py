"""Semantic memory: facts and concepts decoupled from temporal context.

Tulving's distinction: episodic = "what happened to me", semantic = "what I know".
The sleep engine extracts semantic propositions from episodes and stores them
here. Retrieval is dense + filter by topic.

Cycle #78 (2026-05-16): supersession layer (schema v2). A fact can be
marked ``superseded_by=<new_id>`` to express "this is no longer the
current truth, see <new_id>". Retrieval (recall / list_facts /
search_facts / count) filters superseded facts by default. The
historical fact stays in the DB for lineage/audit and is reachable
via ``get(id)``.

Cycle #109 (2026-05-16): provenance schema v3 (Aurelio sfida memoria
compromessa). Pattern ispirato da ProvSEEK 2508.21323 + MemoryGraft
2512.16962 defenses. Tre campi nuovi:

- ``verified_by`` (list[str]): tool-call refs che hanno verificato il
  fact. Esempi: ``"bash:pytest_collect:exit0"``, ``"file:tests/:1708"``,
  ``"url:arxiv.org/abs/2310.11511:sec_3.1"``. Empty list = no verification.
- ``status``: ``"verified" | "model_claim" | "provisional" | "legacy_unverified"``.
  Default = ``"model_claim"`` (fact creato da modello senza evidence).
  ``"legacy_unverified"`` = fact ereditato pre-cycle-109 (migration).
- ``source_signature`` (str | None): hash of source content per detectare
  drift (es. ``"sha256:abc123"``). Optional.

Migration v2→v3: aggiunge le 3 colonne; UPDATE delle righe esistenti
marca tutto come ``status="legacy_unverified"`` (distinguibile da fact
post-fix con status implicito).
"""
from __future__ import annotations

import atexit
import json
import logging
import os
import sqlite3
import threading
import time
import uuid
from collections.abc import Callable, Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from . import embedding
from . import epistemic as _epistemic
from ._telemetry_prefixes import TELEMETRY_TOPIC_PREFIXES as _TELEMETRY_TOPIC_PREFIXES
from .config import _LEGACY_EMBEDDING_MODEL, CONFIG
from .freshness import is_stale
from .provenance_validator import (
    validate_provisional_refs,
    validate_verified_refs,
)

_LOG = logging.getLogger(__name__)


# ── Hang-safety circuit-breaker (2026-06-06) ──────────────────────────────
# A STORE must NEVER block the caller on the embedding. A starved/hung encode
# daemon (alive but slow under heavy concurrent load) or an in-process cold-load
# could otherwise wedge a memory write for MINUTES — a real 40-min save-hang was
# observed under heavy Docker-build resource starvation. When the encode exceeds
# this budget we DEFER: the fact is written with an empty-embedding sentinel
# (instant, keyword-findable, backfilled later) instead of hanging.
_SAVE_ENCODE_BUDGET_S = float(os.environ.get("HIPPO_SAVE_ENCODE_BUDGET_S", "8") or "8")
# Recall query-encode budget (2026-06-06): recall MUST encode the query (it
# cannot DEFER like a save), so on a cold/contended encode daemon it would block
# on the in-process model cold-load (~up to _MODEL_LOCK timeout). On overrun the
# query-encode returns None and recall falls back to INSTANT keyword search —
# never blocks. The warm-daemon path is unchanged. Tune with
# HIPPO_RECALL_ENCODE_BUDGET_S.
#
# 2026-06-13: lowered 8→2, DERIVED (not guessed) from live evidence. After a
# server restart the FIRST recall (encode daemon still cold from preload) hit
# the MCP client request timeout; the SECOND — a full WARM recall (~3s, INCLUDING
# the 3s rerank budget) — succeeded. So the client timeout is provably >= ~3s.
# On encode overrun the cold-path latency is (this budget) + keyword search, and
# the cold path returns BEFORE the rerank, so 2s + keyword(<0.5s) ≈ 2.5s < 3s
# beats even the LOWER bound of the observed timeout. (An adversarial review
# rightly rejected 4s: it's only proven < timeout if the timeout is >4s, which
# the evidence doesn't establish; 2s is bounded under the proven >=3s.) Warm
# encode is <1s, far under 2s, so the warm path is unchanged. The real cure
# remains a warm daemon before serving; this keeps the cold window responsive.
_RECALL_ENCODE_BUDGET_S = float(os.environ.get("HIPPO_RECALL_ENCODE_BUDGET_S", "2") or "2")


def _recall_rerank_budget_s() -> float:
    """Wall-clock budget (s) for the stage-2 CE rerank, read at CALL time.

    Measured 2026-06-13: the CrossEncoder COLD load is ~33s and the steady
    per-query predict ~1.7s; under CPU contention the cold-load was a 10-min
    recall hang (Aurelio killed the MCP call with ESC). On overrun the rerank
    is abandoned and recall keeps the (valid) bi-encoder order — the model
    finishes warming in the background, so the NEXT query reranks. Default
    3.0s leaves headroom over the warm predict while capping the cold path.
    Tune with HIPPO_RECALL_RERANK_BUDGET_S (0 disables the bound)."""
    try:
        return float(os.environ.get("HIPPO_RECALL_RERANK_BUDGET_S", "3.0") or "3.0")
    except ValueError:
        return 3.0


def _encode_prepared_within_budget(
    prepared_text: str, budget_s: float, *, thread_name: str = "hippo-encode",
):
    """Encode ALREADY-PREFIXED text (caller applied as_query / as_passage) in a
    daemon thread joined with a wall-clock budget. Returns None on overrun (the
    worker is abandoned — it finishes harmlessly in the background — and the
    encode daemon is kicked awake); a genuine encode error propagates. Shared
    core of the save (passage→defer) and recall (query→keyword) budgeted encodes.
    """
    box: dict[str, Any] = {}

    def _work() -> None:
        try:
            box["vec"] = embedding.encode(prepared_text)
        except BaseException as exc:  # noqa: BLE001 — re-raised to caller below
            box["err"] = exc

    t = threading.Thread(target=_work, name=thread_name, daemon=True)
    t.start()
    t.join(budget_s)
    if t.is_alive():
        _LOG.warning(
            "encode exceeded %.1fs budget → degrading (save defers / recall "
            "falls back to keyword); kicking the encode daemon awake", budget_s,
        )
        try:
            from . import encode_service as _es
            _es.ensure_running()
        except Exception:  # noqa: BLE001
            pass
        return None
    if "err" in box:
        # DELEGATE-ONLY (MCP server, no daemon, cold): degrade — recall falls
        # back to keyword, save defers — instead of propagating (no in-process
        # cold-load happened, so nothing to wait on).
        if isinstance(box["err"], embedding.EncodeDelegateUnavailable):
            return None
        raise box["err"]
    return box.get("vec")


def _encode_within_budget(text: str, budget_s: float | None = None):
    """Encode `text` for a STORE (applies as_passage), returning None if it can't
    finish within `budget_s` (→ the fact is stored DEFERRED rather than hanging
    the save). `budget_s` defaults to the module constant read at CALL time (so
    it stays test-configurable / env-overridable). A real encode error still
    propagates; only a *slow* encode becomes a deferral — a write must not block.
    """
    if budget_s is None:
        budget_s = _SAVE_ENCODE_BUDGET_S
    return _encode_prepared_within_budget(
        embedding.as_passage(text), budget_s, thread_name="hippo-save-encode",
    )


# Interactive-save WRITE budget (2026-06-06, second proven root of the recurring
# save-block). The encode is already deferred above, but the SQLite WRITE itself
# can still block: the store is WAL + busy_timeout=60000, so when a long
# background write (consolidation BEGIN IMMEDIATE, a bulk store, another session)
# holds the write lock, a concurrent store() WAITS up to 60s on the lock
# (empirically reproduced: 3.77s wait while a holder held the lock 4s).
_SAVE_WRITE_BUDGET_S = float(os.environ.get("HIPPO_SAVE_WRITE_BUDGET_S", "8") or "8")
_PENDING_WRITES: set = set()  # refs so deferred background-write threads aren't GC'd
_PENDING_WRITES_LOCK = threading.Lock()

# ── Deferred-write intent journal (incident 2026-06-10) ─────────────────────
# A deferred store used to live ONLY in a daemon thread + atexit flush: a
# TerminateProcess/kill (no atexit) while the SQLite lock was still held by a
# dream-length writer lost the write AFTER the caller had already received
# ok+deferred (at-most-once masked as success; fact 9e4211057e4d died this
# way). Now the intent is fsync'd to pending_facts.jsonl NEXT TO the db
# BEFORE the caller gets {"deferred": True}; the worker thread appends a
# "done" marker once the write lands; SemanticMemory.__init__ replays orphan
# entries (skip-if-id-exists = idempotent, so the tiny race window between
# is_alive() and the journal append can only produce a harmless no-op entry).

_JOURNAL_NAME = "pending_facts.jsonl"
#: store() kwargs that survive the journal round-trip (callables dropped).
_JOURNAL_KWARGS_WHITELIST = ("embed", "return_replaced", "hook_token")
#: a .replay-*.jsonl older than this is an orphan of a crashed replayer.
_REPLAY_CLAIM_STALE_S = 60.0


def _slow_txn_warn_s() -> float:
    """Threshold (s) above which a held _connect() context logs a warning.

    Step 1 of the 2026-06-10 long-writer hunt: the lock incidents proved
    SOMETHING holds the write lock for >30s but nothing names it. Env
    ENGRAM_SLOW_TXN_WARN_S tunes the threshold (default 2.0s)."""
    try:
        return float(os.environ.get("ENGRAM_SLOW_TXN_WARN_S", "2.0"))
    except ValueError:
        return 2.0


def _journal_path_for(db_path) -> Path | None:
    """pending_facts.jsonl beside the semantic db; None for :memory:/unset."""
    if not db_path or str(db_path) == ":memory:":
        return None
    try:
        return Path(db_path).parent / _JOURNAL_NAME
    except (TypeError, ValueError):
        return None


def _journal_append(jpath: Path, obj: dict) -> bool:
    """Append one JSON line, fsync'd (must survive an immediate kill).
    Never raises: the journal is a safety net, not a new failure mode."""
    try:
        jpath.parent.mkdir(parents=True, exist_ok=True)
        with open(jpath, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(obj) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        return True
    except OSError as exc:
        _LOG.warning("deferred-write journal append failed: %s", exc)
        return False


def _json_safe_store_kwargs(kwargs: dict) -> dict:
    return {k: kwargs[k] for k in _JOURNAL_KWARGS_WHITELIST if k in kwargs}


def _fact_from_dict(d: dict) -> Fact:
    """Rebuild a Fact from a journal entry, tolerant to schema drift."""
    import dataclasses as _dc
    valid = {f.name for f in _dc.fields(Fact)}
    return Fact(**{k: v for k, v in d.items() if k in valid})


def _episode_from_dict(d: dict):
    """Rebuild an Episode (with its nested Trace list) from a journal entry.

    Bug-hunt F2/F4 (2026-06-13): the deferred-write journal must survive a
    kill for EPISODES too, not just facts. ``dataclasses.asdict`` flattens
    the nested ``traces`` to plain dicts, so we rebuild the Trace objects
    here; unknown keys are dropped (schema-drift tolerant)."""
    import dataclasses as _dc

    from .episode import Episode, Trace
    valid = {f.name for f in _dc.fields(Episode)}
    kw = {k: v for k, v in d.items() if k in valid}
    if isinstance(kw.get("traces"), list):
        kw["traces"] = [
            Trace(**t) if isinstance(t, dict) else t for t in kw["traces"]
        ]
    return Episode(**kw)


def _durable_checkpoint(db_path) -> None:
    """Force WAL -> main db + fsync so replayed writes are on disk BEFORE the
    crash journal is unlinked. With synchronous=NORMAL a store is not durable
    until a checkpoint, so a power-cut in the unlink gap would otherwise lose
    both the replayed write and its journal. Best-effort: never blocks boot."""
    if db_path is None:
        return
    import os as _os
    import sqlite3 as _sql
    try:
        conn = _sql.connect(str(db_path), timeout=5.0)
        try:
            conn.execute("PRAGMA wal_checkpoint(FULL)")
        finally:
            conn.close()
    except _sql.Error:
        return
    try:
        fd = _os.open(str(db_path), _os.O_RDONLY)
        try:
            _os.fsync(fd)
        finally:
            _os.close(fd)
    except OSError:
        pass


def _replay_pending_facts(memory) -> int:
    """Replay crash-orphaned deferred writes for this db. Returns count.

    Claim-by-rename makes concurrent boots safe (loser's rename raises);
    stale .replay-* claims from a crashed replayer are re-claimed after
    _REPLAY_CLAIM_STALE_S. Idempotency is keyed by the per-deferral NONCE: a
    nonce-tagged entry is skipped ONLY when its own deferral was marked done (the
    background store landed), so a genuinely-newer deferred UPDATE replays even
    though its content-hash id is already present, and a stale done-marker of an
    EARLIER deferral of the same id no longer masks it. Legacy (pre-nonce) entries
    keep the old id-presence/done guard for back-compat (data-loss hunt #1)."""
    jpath = _journal_path_for(getattr(memory, "db_path", None))
    if jpath is None:
        return 0
    claims: list[Path] = []
    if jpath.exists():
        claim = jpath.with_name(f"{jpath.stem}.replay-{os.getpid()}.jsonl")
        try:
            jpath.rename(claim)
            claims.append(claim)
        except OSError:
            pass  # another process claimed the journal first
    try:
        now = time.time()
        for stale in jpath.parent.glob(f"{jpath.stem}.replay-*.jsonl"):
            if stale in claims:
                continue
            try:
                if now - stale.stat().st_mtime < _REPLAY_CLAIM_STALE_S:
                    continue
                mine = jpath.with_name(
                    f"{jpath.stem}.replay-{os.getpid()}-{len(claims)}.jsonl")
                stale.rename(mine)
                claims.append(mine)
            except OSError:
                continue
    except OSError:
        pass
    replayed = 0
    for claim in claims:
        _replayed_at_start = replayed
        # Idempotency is keyed by the per-deferral NONCE, not the fact id: a
        # done-marker proves THIS deferral's background store landed. Tracking
        # nonces (not ids) lets a genuinely-newer deferred UPDATE replay even
        # though its content-hash id is already present, while a stale done:X from
        # an EARLIER completed deferral of the same id no longer masks it
        # (data-loss hunt #1, 2026-06-14).
        done_nonces: dict[str, set[str]] = {}
        done_legacy: set[str] = set()  # pre-nonce done-markers (id only)
        entries: dict[str, dict] = {}
        try:
            lines = claim.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in lines:
            try:
                obj = json.loads(line)
            except ValueError:
                continue
            if obj.get("kind") == "done" and obj.get("id"):
                _dn = obj.get("nonce")
                if _dn:
                    done_nonces.setdefault(obj["id"], set()).add(_dn)
                else:
                    done_legacy.add(obj["id"])
            elif obj.get("kind") in ("fact", "episode"):
                _payload = obj.get(obj["kind"]) or {}
                fid = _payload.get("id")
                if fid:
                    entries[fid] = obj
        failed = 0
        for fid, obj in entries.items():
            _n = obj.get("nonce")
            if _n is not None:
                # New nonce-tagged entry: skip ONLY if THIS deferral was marked
                # done (its background store landed). Do NOT skip on id-presence —
                # for a content-hash id an UPSERT update journals against an
                # already-present row, so id-presence is the normal precondition.
                if _n in done_nonces.get(fid, ()):
                    continue
            elif fid in done_legacy or memory.get(fid) is not None:
                # Pre-nonce journal entry (back-compat): keep the old id-presence/
                # done guard so an upgrade never double-applies a legacy entry that
                # had no nonce to disambiguate a landed write from a lost one.
                continue
            try:
                # F2/F4: rebuild the right object for the journal kind. A
                # journal lives beside ONE db (semantic/ or episodes/), so the
                # memory passed here matches the kind it persisted.
                if obj.get("kind") == "episode":
                    _obj = _episode_from_dict(obj["episode"])
                else:
                    _obj = _fact_from_dict(obj["fact"])
                memory.store(
                    _obj,
                    **_json_safe_store_kwargs(obj.get("store_kwargs") or {}),
                )
                replayed += 1
            except Exception:  # noqa: BLE001 — one bad entry must not kill the rest
                failed += 1
                _LOG.warning("pending deferred-write replay failed for %s", fid,
                             exc_info=True)
        if replayed > _replayed_at_start:
            # Durability barrier: the writes just replayed must reach disk
            # BEFORE we drop the journal — else a power-cut in this gap loses
            # both (synchronous=NORMAL doesn't fsync each commit).
            _durable_checkpoint(getattr(memory, "db_path", None))
        if failed == 0:
            # Only drop the claim once EVERY entry landed (or was provably already
            # applied). If any store() raised (e.g. SQLite 'database is locked' past
            # busy_timeout during concurrent consolidation), KEEP the claim file: the
            # stale-recovery glob above retries it on a later boot once it ages past
            # _REPLAY_CLAIM_STALE_S — instead of unlinking it and losing the un-stored
            # deferred writes forever (the exact at-most-once data loss the journal
            # exists to prevent; review 2026-06-20). Re-replay is idempotent (nonce/
            # done-marker guards + UPSERT), so re-applying the entries that DID land is safe.
            try:
                claim.unlink()
            except OSError:
                pass
    if replayed:
        _LOG.warning(
            "replayed %d deferred fact write(s) from the crash journal", replayed,
        )
    return replayed


def store_within_budget(
    memory, fact, *, budget_s: float | None = None, **store_kwargs,
) -> dict:
    """Persist `fact` via `memory.store` without letting the INTERACTIVE caller
    block on a contended SQLite write lock.

    The store DB is WAL + busy_timeout=60000: when a long background write holds
    the write lock, a concurrent store() waits up to 60s. This runs the write on
    a daemon thread joined for ``budget_s``:

      - completes in time → ``{"deferred": False, "result": <store() return>}``
      - still blocked      → ``{"deferred": True}`` (returned immediately; the
        thread keeps going and completes the write in the background once the lock
        frees — durable, the write is NOT lost)

    A genuine store() error raised WITHIN the budget propagates to the caller.
    Mirrors the encode circuit-breaker, applied to the write path."""
    budget = _SAVE_WRITE_BUDGET_S if budget_s is None else budget_s
    box: dict[str, Any] = {}
    # Per-deferral nonce (data-loss hunt #1, 2026-06-14): tags THIS deferral so a
    # later boot replay re-applies a genuinely-newer deferred UPDATE instead of
    # masking it on id-presence or a stale prior done-marker of the SAME id. The
    # done-marker (written when the background store lands) echoes the nonce.
    _nonce = os.urandom(8).hex()

    def _work() -> None:
        try:
            box["result"] = memory.store(fact, **store_kwargs)
            # Incident 2026-06-10: if the caller journaled this write (budget
            # elapsed), mark it done so boot replay won't re-apply it. A
            # completion racing the caller's journal append just leaves an
            # un-marked entry — harmless, replay skips existing ids.
            if box.get("journaled"):
                jp = _journal_path_for(getattr(memory, "db_path", None))
                if jp is not None:
                    _journal_append(
                        jp, {"kind": "done", "id": fact.id, "nonce": _nonce}
                    )
        except BaseException as exc:  # noqa: BLE001 — surfaced to caller if in time
            box["err"] = exc
            # Never swallow: a write that fails AFTER the budget elapses (caller
            # already got {"deferred": True}) would otherwise vanish without a
            # trace. Log it regardless; in-budget failures are ALSO re-raised.
            _LOG.warning("deferred/budgeted store failed: %s", exc, exc_info=True)
        finally:
            with _PENDING_WRITES_LOCK:
                _PENDING_WRITES.discard(threading.current_thread())

    t = threading.Thread(target=_work, name="hippo-store-budget", daemon=True)
    with _PENDING_WRITES_LOCK:
        _PENDING_WRITES.add(t)
    t.start()
    t.join(budget)
    if t.is_alive():
        _LOG.warning(
            "store exceeded %.1fs write budget → DEFERRED (a long write holds the "
            "SQLite write lock); completing in the background", budget,
        )
        # Persist the INTENT before replying: a kill (no atexit) between this
        # reply and the background completion must not lose the write.
        jp = _journal_path_for(getattr(memory, "db_path", None))
        if jp is not None:
            import dataclasses as _dc

            # F2/F4 (2026-06-13): tag the entry by object type so the boot
            # replay can rebuild the right thing. The episode hot path
            # (hippo_record_episode) reuses this primitive; without the tag a
            # deferred episode was journaled as kind="fact", rebuilt as a Fact,
            # and — worse — never replayed (EpisodicMemory had no replay), so a
            # kill before the background write silently dropped it.
            from .episode import Episode as _Episode
            _is_ep = isinstance(fact, _Episode)
            _key = "episode" if _is_ep else "fact"
            entry = {
                "kind": _key, "ts": time.time(), "nonce": _nonce,
                _key: _dc.asdict(fact),
                "store_kwargs": _json_safe_store_kwargs(store_kwargs),
            }
            if _journal_append(jp, entry):
                box["journaled"] = True
        return {"deferred": True}
    if "err" in box:
        raise box["err"]
    return {"deferred": False, "result": box.get("result")}


def _flush_pending_writes(timeout_s: float | None = None) -> int:
    """Wait (bounded) for in-flight deferred writes before interpreter exit.

    ``store_within_budget`` offloads a contended SQLite write to a *daemon*
    thread and returns ``{"deferred": True}`` once the budget elapses. Daemon
    threads are terminated abruptly at process exit, so without this an in-flight
    write would be LOST at shutdown — the durability promised by
    ``store_within_budget`` only holds while the interpreter stays alive.
    Registered via ``atexit`` so a normal shutdown gives pending writes a chance
    to land. Returns the count still unfinished after the timeout (best-effort;
    logged). Override the wait via ``HIPPO_FLUSH_ON_EXIT_S`` (default 30s; 0
    disables the wait).
    """
    if timeout_s is None:
        timeout_s = float(os.environ.get("HIPPO_FLUSH_ON_EXIT_S", "30") or "30")
    with _PENDING_WRITES_LOCK:
        pending = [t for t in _PENDING_WRITES if t.is_alive()]
    if not pending:
        return 0
    deadline = time.monotonic() + max(0.0, timeout_s)
    for t in pending:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        t.join(remaining)
    still = sum(1 for t in pending if t.is_alive())
    if still:
        _LOG.warning(
            "interpreter exit with %d unfinished deferred write(s) after %.0fs "
            "flush budget — data may be lost", still, timeout_s,
        )
    return still


atexit.register(_flush_pending_writes)


# Cycle #109: status enum — extension requires schema migration.
# Cycle #137 (2026-05-17): added "orphaned" for L2 reconciler mutation.
# Cycle #138 (2026-05-18): added "quarantined" for the anti-confab gate
# on write. A fact is "quarantined" when the gate (L1 keyword detectors
# and/or L3 validate_claim) flagged it AT WRITE TIME but the operator
# chose gate_mode='downgrade' rather than 'reject' — the suspect claim
# lands on disk for audit but is hidden from default recall, exactly
# like 'orphaned' (a post-hoc analog detected by the L2 reconciler).
_VALID_STATUSES = frozenset({
    "verified",            # backed by verified_by tool-call refs
    "model_claim",         # no verification (default for new fact)
    "provisional",         # research finding / hypothesis (no row_id)
    "legacy_unverified",   # pre-cycle-109 fact (migration default)
    "orphaned",            # cycle 137: L2 reconciler scrubbed
    "quarantined",         # cycle 138: anti-confab gate downgraded at write
    "user_belief",         # Giro 2 2026-07-15: unverified USER assertion of fact —
    #                        hidden from default recall (anti-sycophancy), rehabilitable
})

# Cycle #109 S4-A: trust hierarchy for ``min_status`` recall filter.
# Higher rank = stronger provenance. ``min_status=X`` keeps rows where
# ``_STATUS_RANK[row.status] >= _STATUS_RANK[X]``.
# Cycle #137: orphaned sits BELOW legacy_unverified.
# Cycle #138: quarantined sits BETWEEN orphaned and legacy_unverified —
# weaker than 'legacy_unverified' (which is at least a quiet pre-cycle
# row, no detectors fired) but stronger than 'orphaned' (which is a
# post-hoc L2 reconciler flip after the row has lived on disk).
_STATUS_RANK = {
    "orphaned": -2,
    "quarantined": -1,
    "user_belief": -1,     # Giro 2: below model_claim, hidden from default recall like
    #                        quarantined (an uncorroborated user assertion is not a fact)
    "legacy_unverified": 0,
    "provisional": 1,
    "model_claim": 2,
    "verified": 3,
}


def _validate_min_status(min_status: str | None) -> None:
    """Raise ValueError when ``min_status`` is set but unknown."""
    if min_status is not None and min_status not in _STATUS_RANK:
        raise ValueError(
            f"min_status must be one of {sorted(_STATUS_RANK)!r}, "
            f"got {min_status!r}"
        )


def _row_passes_status_filter(
    row: sqlite3.Row, *,
    exclude_legacy: bool = False,
    min_status: str | None = None,
) -> bool:
    """Apply provenance filter to a raw SQLite row (pre-Fact deserialization).

    Tolerant to legacy rows missing the ``status`` column — defaults to
    ``"model_claim"`` (same behaviour as :meth:`SemanticMemory._row`).
    """
    try:
        status = row["status"] or "model_claim"
    except (IndexError, KeyError):
        status = "model_claim"
    if exclude_legacy and status == "legacy_unverified":
        return False
    if min_status is not None:
        return _STATUS_RANK.get(status, 0) >= _STATUS_RANK[min_status]
    return True


_SCHEMA = """
CREATE TABLE IF NOT EXISTS facts (
    id TEXT PRIMARY KEY,
    proposition TEXT NOT NULL,
    topic TEXT NOT NULL,
    confidence REAL NOT NULL,
    source_episodes TEXT NOT NULL,
    created_at REAL NOT NULL,
    embedding BLOB NOT NULL,
    superseded_by TEXT,
    superseded_at REAL,
    superseded_reason TEXT,
    verified_by TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL DEFAULT 'model_claim',
    source_signature TEXT,
    -- Cycle 160 (2026-05-19) pattern card schema v5. All four nullable
    -- / empty for backward compat. Empirical motivation: cycle 160 bench
    -- measured TPR@20=70% for semantic-only retrieval; the residual 30%
    -- miss is wording-mismatch that explicit metadata can recover.
    trigger_keywords TEXT,
    applicable_when TEXT,
    worked_example TEXT,
    lineage_to TEXT,
    -- Cycle 2026-05-27 round 12 (F-fix) provenance schema v6.
    -- writer_role distinguishes 'system_hook' / 'user' / 'agent_inference'
    -- for the anti_confab_gate trusted-hook bypass. meta_narrative=1
    -- marks retrospective continuity facts (pre-compact masters, session
    -- recaps). Both required together to skip L1.x detectors.
    writer_role TEXT NOT NULL DEFAULT 'agent_inference',
    meta_narrative INTEGER NOT NULL DEFAULT 0,
    -- v8 (2026-06-03, buco #3 validita temporale). Timestamp dell'ultima
    -- verifica del fatto; freshness/decay (engram/freshness.py) lo usa per
    -- declassare i capability-claim scaduti per eta (caso A2A "prima
    -- funzionava"). Nullable: il contratto "default = created_at" e'
    -- imposto da store() (lo setta) e _row (coalesce NULL->created_at),
    -- perche' SQLite ADD COLUMN non ammette DEFAULT su un'altra colonna.
    last_verified_at REAL,
    -- v9 (2026-06-03, Sorella C BLOCKING) — modello di embedding per-riga.
    -- store() lo stampa col modello attivo (embedding.model_signature()).
    -- NULL == riga legacy pre-v9 == modello storico (_LEGACY_EMBEDDING_MODEL).
    -- Il recall filtra COALESCE(embedding_model, legacy) = modello-attivo su
    -- entrambi i path: blocca il poisoning silenzioso da vettori stessa-dim
    -- ma di un modello diverso (cosine incomparabile). Default invariato
    -- (attivo == legacy): NULL e stamp passano entrambi -> recall identico.
    embedding_model TEXT,
    -- v10 (2026-06-14) valid-time bi-temporale. Limite SUPERIORE di validita'
    -- del fatto: oltre questo istante non e' piu' vero e il recall lo esclude
    -- (hard-expire), a prescindere da eta'/half-life (a differenza di
    -- last_verified_at, che e' decay graduale). NULL = nessuna scadenza (i
    -- fatti non scadono salvo dichiarazione esplicita del chiamante). Recall
    -- byte-identico finche' nessuno la setta. Differenziatore bi-temporale vs
    -- Mem0/Zep (invalidation senza valid-time esplicito). Additiva, nullable.
    valid_until REAL,
    -- v11 (2026-06-19) edge di DERIVAZIONE LOGICA tipizzato (ATMS depends_on).
    -- DISTINTO da lineage_to (che e' un puntatore NARRATIVO/successore-di-
    -- sessione, --lineage-to auto, 95% cross-topic — R26 lo ha falsificato come
    -- edge logico). derives_from = id dei fatti la cui VERITA' giustifica questo:
    -- se uno di essi viene superseduto/contraddetto, justified_memory.propagate
    -- ritrae transitivamente questo fatto. Comma-separated, nullable, additiva.
    -- Vuoto per i fatti esistenti => propagate resta dormiente finche' il
    -- write-path non lo popola (hippo_remember derives_from=...).
    derives_from TEXT,
    -- v12 (2026-06-20) write-time grounding score (0-100): L4 source-entailment
    -- (grounding_gate, AUROC 0.971) calcolato dal gate e ora PERSISTITO (era scartato).
    -- Trust-coordinate write-time per provenance-conditioned recall/answer. Nullable.
    grounding_score REAL,
    -- v15 (2026-07-19) write-time confidence_tier (high/borderline/low/
    -- unverified): the judge's CONFIDENCE band, persisted so recall/audit can
    -- distinguish a borderline 'held-for-review' quarantine from a hard
    -- contradiction. Additive, nullable, no backfill.
    confidence_tier TEXT,
    -- v13 (2026-07-05) EVENT time bi-temporale (asserted/valid-FROM): quando il
    -- fatto e' stato detto/era vero, DISTINTO da created_at (transaction time =
    -- quando il sistema l'ha imparato). created_at resta mai-retrodatato, cosi'
    -- staleness half-life e anti-spoof fail-closed restano fondati; asserted_at
    -- guida l'age-gap del reconcile e la storia temporale, e un valore nel
    -- futuro e' LEGITTIMO (appuntamenti, scadenze), non spoofing. Root-cause
    -- 2026-07-05: stipare l'event time in created_at rendeva invisibile al
    -- recall l'83% di uno store retro/post-datato. Nullable, additiva, NO
    -- backfill: NULL = "event time sconosciuto" -> fallback created_at.
    asserted_at REAL,
    -- v14 (2026-07-13) etichetta epistemica (transfer cortex #1): JSON
    -- {"kind":"proven"|"unbeaten"|"refuted", ...} — il TIPO di garanzia,
    -- ortogonale a status (chi garantisce vs che garanzia). Transizioni
    -- monotone via set_epistemic (engram/epistemic.py), refuted assorbente.
    -- Nullable, additiva, NO backfill: NULL = non etichettato (default).
    epistemic TEXT
);
CREATE INDEX IF NOT EXISTS idx_facts_topic ON facts(topic);
"""
# idx_facts_superseded_by lives in _migrate_v1_to_v2 (supersession),
# idx_facts_status lives in _migrate_v2_to_v3 (provenance) — both
# because a pre-migration DB has no such columns when _SCHEMA executes,
# so the index DDL would fail "no such column" before ALTER TABLE.


def _glob_to_like(pattern: str) -> str:
    """Cycle #79: translate small glob (``*``/``?``) into SQL LIKE pattern,
    escaping LIKE-special ``%`` and ``_`` with ``\\`` (used as ESCAPE char
    at call site)."""
    out: list[str] = []
    for ch in pattern or "":
        if ch == "\\":
            out.append("\\\\")
        elif ch == "%":
            out.append("\\%")
        elif ch == "_":
            out.append("\\_")
        elif ch == "*":
            out.append("%")
        elif ch == "?":
            out.append("_")
        else:
            out.append(ch)
    return "".join(out)


def _like_escape_literal(s: str) -> str:
    """Escape a string so it matches LITERALLY inside a ``LIKE`` pattern.

    Unlike :func:`_glob_to_like`, ``*`` and ``?`` stay literal too — the input
    is a plain substring, not a glob. Escapes the LIKE metacharacters ``%`` and
    ``_`` (and ``\\`` itself) with backslash, for use with ``ESCAPE '\\'``.
    Correctness-hunt #3 HIGH-3: search_facts treated ``node_engine`` as a glob
    (``_`` = any char) and over-matched ``nodeXengine``.
    """
    return (s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_"))


class SupersedeError(ValueError):
    """Raised on invalid arguments to :meth:`SemanticMemory.supersede`.

    Cases (cycle #78):
        - self-supersede (old_id == new_id)
        - unknown old_id
        - unknown new_id
    """


class SupersedeConflict(RuntimeError):
    """Raised when ``old_id`` is already superseded by a *different* fact
    than the one declared in the new call.

    Caller decides how to resolve: explicit chain (declare ``old→middle``
    AND ``middle→new``) or accept the prior assignment.
    """


#: Current target schema version for the ``semantic`` db. Bump together
#: with the migrations ladder in ``__init__`` so external callers (tests,
#: migration audits) can assert ``schema_version(c, "semantic") ==
#: _SEMANTIC_TARGET_VERSION`` instead of repeating the magic number.
#:
#: History:
#:   v0 — pre-cycle #78 (CREATE TABLE bootstrap, no migration).
#:   v1 — cycle #78 alpha (intermediate).
#:   v2 — cycle #78 supersession columns (``superseded_by`` + history).
#:   v3 — cycle #109 provenance (``verified_by``/``status``/sig).
#:   v4 — cycle 157 partial UNIQUE INDEX cross-process safety.
#:   v5 — cycle 160 pattern card schema (trigger_keywords +
#:        applicable_when + worked_example + lineage_to).
#:   v6 — cycle 2026-05-27 round 12 F-fix (writer_role + meta_narrative)
#:        for anti_confab_gate trusted-hook bypass.
#:   v7 — cycle 2026-05-27 round 13 P0c transactional rollback
#:        (facts_undo_log table for forget/supersede undo).
#:   v8 — 2026-06-03 buco #3 validita temporale (``last_verified_at`` REAL,
#:        nullable; default=created_at imposto da store/_row). Wira
#:        freshness.is_stale come cutoff nel recall.
#:   v9 — 2026-06-03 buco silent-poisoning (Sorella C): colonna per-riga
#:        ``embedding_model`` + filtro recall per-modello su entrambi i path.
#:        Additiva, nullable; NULL == legacy == _LEGACY_EMBEDDING_MODEL.
#:   v10 — 2026-06-14 valid-time ``valid_until`` (hard-expire nel recall).
#:   v11 — 2026-06-19 typed derivation edge ``derives_from`` (ATMS).
#:   v12 — 2026-06-20 write-time ``grounding_score`` persistito.
#:   v13 — 2026-07-05 bi-temporal EVENT time ``asserted_at`` (valid-FROM):
#:        created_at resta transaction time (guardie freshness/anti-spoof
#:        fondate); asserted_at guida reconcile age-gap + answer-with-history.
#:   v14 — 2026-07-13 etichetta epistemica ``epistemic`` (transfer cortex #1).
#:        NB: questo numero è il RUNNER. Il 2026-07-13 la colonna era stata
#:        aggiunta a _SCHEMA e ``_migrate_v13_to_v14`` scritta e registrata,
#:        ma il target era rimasto 13 → la migrazione non girava MAI: i DB
#:        nuovi (tutti i test) nascevano già a posto, gli store ESISTENTI
#:        restavano senza colonna e OGNI write moriva con "table facts has no
#:        column named epistemic" (store reale, 6120 fatti, 2026-07-15).
#:        Registrare una migrazione senza alzare il target = non averla.
_SEMANTIC_TARGET_VERSION: int = 14

#: v8 (2026-06-03) — half-life di default per il decadimento di freshness
#: nel recall. is_stale(age, half_life, floor=0.5) e' True quando il fattore
#: di decadimento scende sotto 0.5, cioe' quando ``age_days > half_life_days``.
#: 2026-06-09 (Aurelio "un mese e mezzo"): 90 -> 45 giorni. Un ricordo non
#: ri-verificato/ri-usato da oltre ~1.5 mesi esce dalla vista di default. La
#: finestra piu' corta e' resa sicura dal bump-on-recall (vedi recall()):
#: l'eta si misura dall'ULTIMO USO, non dalla creazione, quindi i ricordi
#: attivi non svaniscono. Parametro unico, tunabile per-namespace in futuro.
_DEFAULT_HALF_LIFE_DAYS: float = 45.0

#: 2026-06-09 — bump-on-recall: un recall che restituisce un fatto ne rinfresca
#: ``last_verified_at`` all'orologio del SERVER (mai futuro -> anti-spoof intatto;
#: i fatti stantii sono filtrati PRIMA, quindi non vengono mai ringiovaniti).
#: Soglia di refresh = META' della finestra: si ringiovanisce SOLO un fatto la
#: cui ultima verifica supera mezza half-life (oltre il "giro di boa"). I fatti
#: ancora freschi NON vengono toccati -> nessuna scrittura ne' invalidazione
#: cache sul caso comune; solo quelli che si avvicinano alla soglia (e quindi
#: rischiano di sparire) vengono rinfrescati. Opt-out: ENGRAM_BUMP_ON_RECALL=0.
_BUMP_REFRESH_THRESHOLD_S: float = _DEFAULT_HALF_LIFE_DAYS * 86400.0 * 0.5


def _bump_busy_timeout_ms() -> int:
    """SQLite busy_timeout (ms) for the bump-on-recall UPDATE, read at call
    time. The bump is a best-effort freshness write on the READ path: it must
    NEVER make recall wait the full 60s store busy_timeout on a contended
    writer (bug-hunt F3 2026-06-13: a held write lock blocked recall ~30-60s).
    A short bound lets the lock fail fast; the failure is swallowed and recall
    stays responsive. Tune with HIPPO_BUMP_BUSY_TIMEOUT_MS (default 500)."""
    try:
        return max(0, int(os.environ.get("HIPPO_BUMP_BUSY_TIMEOUT_MS", "500")))
    except ValueError:
        return 500

#: Cycle 171/172 (2026-05-22) — canonical byte length of a serialized
#: fact / episode / skill embedding. The active model is
#: all-MiniLM-L6-v2 (384 dim) and ``verimem.embedding.serialize`` writes
#: float32 → 384*4 = 1536 bytes. SQL ``WHERE length(<col>) = ?``
#: rejects malformed blobs (``b""`` placeholders left by ``clp save``
#: pre-fix, or mid-migration dim mismatches) before they reach
#: np.stack. SQL-side filter is critical: a Python-side deserialize
#: loop regressed cycle 135 sub-linear scaling p50(2000)/p50(500)
#: from <3× to 4.15× (the 2026-05-21 mem-architect attempt).
#: Imported by memory.py and skill.py to extend the cycle 171 fix
#: to all np.stack callers.
#:
#: DIM-DYNAMIC + RUNTIME-LIVE (harden 2026-06-07): ``_EXPECTED_EMBEDDING_BYTES``
#: is exposed via the module ``__getattr__`` below (PEP 562) so EVERY access
#: recomputes ``embedding.expected_embedding_bytes()`` (= ``CONFIG.embedding_dim
#: * 4``) at call time — never a literal, never frozen at import. The earlier
#: ``_EXPECTED_EMBEDDING_BYTES = embedding.expected_embedding_bytes()`` froze the
#: value at IMPORT: a runtime embedding-model/dim switch (MiniLM-384 -> e5-768)
#: then updated ``model_signature()`` live but left this byte-filter at the OLD
#: dim -> every new-dim vector silently excluded from recall (blackout, zero
#: error). memory.py / skill.py do ``from .semantic import
#: _EXPECTED_EMBEDDING_BYTES`` INSIDE their query methods on every call, so this
#: resolves to the live value for them too (PEP 562 covers the ``from import``
#: path). Internal callers in this module call
#: ``embedding.expected_embedding_bytes()`` directly — a bare-name global read
#: does NOT trigger module ``__getattr__``.


def __getattr__(name: str) -> int:
    if name == "_EXPECTED_EMBEDDING_BYTES":
        return embedding.expected_embedding_bytes()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

#: v9 — modello con cui sono stati prodotti i vettori pre-v9 (righe con
#: ``embedding_model`` NULL). Importato da .config (riga import in cima) come
#: costante FROZEN (MiniLM storico), DECOUPLED dal default ATTIVO (multilingue
#: dal flip 2026-06-04): un NULL resta MiniLM ed e' ESCLUSO dal recall sotto
#: modello attivo diverso, senza includere vettori legacy cross-spazio
#: (anti-poisoning BUCO 2). Le eligible vengono re-embeddate dal flip -> niente
#: perdita reale; le non-eligible (gia' fuori recall) restano nel DB.
# _LEGACY_EMBEDDING_MODEL: importato sopra da .config (NON ridefinito qui).

# SCAN-68 (audit 2026-06-02, NONNA): denylist namespace di telemetria-macchina
# (blob di stato, mai conoscenza) per il recall GENERICO (topic=None). Applicata
# in ENTRAMBI i path (cache fast-path E legacy SQL) per coerenza di contratto
# — prima era solo nel cache-path (asimmetria trovata dall'audit-agente).
# NB: 'emerging_skill/' RIMOSSO dalla denylist: sono skill auto-scoperte
# (conoscenza potenziale) -> la gate corretta e' lo STATUS (quarantine), non il
# topic; se promosse a non-quarantined devono tornare richiamabili.
# 'test/' NON in denylist: i fixture usano topic='test/...'.
#: Telemetry topic prefixes excluded from a generic (topic=None) recall.
#: SINGLE SOURCE OF TRUTH = verimem._telemetry_prefixes.TELEMETRY_TOPIC_PREFIXES
#: (imported at module top as _TELEMETRY_TOPIC_PREFIXES), SHARED with the
#: write-time admission gate so the read-side denylist and the write-side router
#: can never drift (the 2026-06-13 live-recall leak WAS exactly that drift). The
#: SQL denylist AND the Python predicate _is_telemetry_topic below both derive
#: from that tuple.
_TELEMETRY_DENYLIST_CLAUSES: tuple[str, ...] = tuple(
    f"topic NOT LIKE '{p}%'" for p in _TELEMETRY_TOPIC_PREFIXES
)
_TELEMETRY_DENYLIST_SQL: str = "".join(
    f" AND {c}" for c in _TELEMETRY_DENYLIST_CLAUSES
) + " "


def _is_telemetry_topic(topic: str | None) -> bool:
    """Python mirror of _TELEMETRY_DENYLIST_CLAUSES (same prefixes)."""
    t = topic or ""
    return any(t.startswith(p) for p in _TELEMETRY_TOPIC_PREFIXES)


def _topic_prefix_upper(prefix: str) -> str:
    """Half-open upper bound for an INDEXED prefix range scan: the smallest
    string strictly greater than every string that starts with ``prefix``.

    Used so a tenant-scoped recall can phrase ``topic LIKE 'p%'`` as
    ``topic >= p AND topic < p⁺`` — the range form drives ``idx_facts_topic``
    (B-tree prefix scan, O(N_tenant)) whereas ``LIKE`` cannot use the index and
    degrades to a full ``superseded_by`` scan (O(N_total)). Measured 203ms→0.16ms
    @1M rows / 10k tenants once ANALYZE stats exist
    (arch-lab/sistema/multitenant_scan_v2.py). Increments the last code point;
    the ASCII scope prefixes (``user:``/``agent:``/``run:`` + ids + ``/``) never
    hit the max-code-point guard. Returns ``prefix`` unchanged when empty."""
    if not prefix:
        return prefix
    last = ord(prefix[-1])
    if last >= 0x10FFFF:  # pragma: no cover — unreachable for scope prefixes
        return prefix + "\U0010FFFF"
    return prefix[:-1] + chr(last + 1)


def _is_unverified_conversational(fact: object) -> bool:
    """A conversational_promotion row that hasn't been verified — the
    anti-laundering class both warm recall paths exclude by default."""
    return (
        getattr(fact, "writer_role", "") == "conversational_promotion"
        and getattr(fact, "status", "") != "verified"
    )


def _fact_is_stale(
    last_verified_at: float | None,
    created_at: float,
    now: float,
    half_life_days: float = _DEFAULT_HALF_LIFE_DAYS,
    *,
    valid_until: float | None = None,
    ignore_age: bool = False,
) -> bool:
    """v8 (2026-06-03) buco #3: True se il fatto e' scaduto per eta.

    ``base`` = ``last_verified_at``, con fallback ``created_at`` (contratto
    di default v8: un fatto e' verificato quando creato). Delega a
    ``freshness.is_stale`` (single source of truth del decadimento), che con
    ``floor=0.5`` ritorna True quando ``age_days > half_life_days``.
    Guardia: base None (impossibile post-migration, ma difensivo) -> non
    stantio (nessuna esclusione spuria).

    ANTI-SPOOF v8.1 (2026-06-03, buco #3b — stessa classe del buco #1
    writer_role caller-spoofabile): un timestamp di verifica nel FUTURO e'
    impossibile. Senza questa guardia un caller salverebbe
    ``last_verified_at = now + anni`` -> ``age_days < 0`` ->
    ``decay_factor`` (freshness.py:22) ritorna 1.0 -> mai stantio -> #3
    aggirato. FAIL-CLOSED: ``base > now`` => stantio (escluso). NON un clamp
    a ``now`` (che renderebbe il fatto FRESCO = esattamente l'obiettivo
    dello spoofer): un timestamp impossibile e' un segnale di manomissione,
    non un dato da normalizzare. Vale per QUALSIASI campo (last_verified_at
    o created_at, entrambi caller-controlled) e per QUALSIASI path di
    scrittura (store, SQL diretto, migrazione): la fiducia sta nel punto di
    DECISIONE, non nella scrittura.
    """
    # v10 (2026-06-14) valid-time bi-temporale: hard-expire. Un valid_until nel
    # passato (o == now) significa che il fatto ha smesso di essere vero per
    # natura (es. "deploy in corso" a deploy finito) -> stantio SUBITO, a
    # prescindere dall'eta/half-life. Cutoff netto, NON decadimento graduale.
    # None = nessuna scadenza. Precede il calcolo del decay (valutato per
    # primo, e' piu' forte: un fatto scaduto e' escluso anche se "fresco").
    if valid_until is not None and valid_until <= now:
        return True
    base = last_verified_at if last_verified_at is not None else created_at
    if base is None:
        return False
    if base > now:
        return True  # verifica nel futuro = impossibile = spoof -> fail-closed
    # v14 deep-recall (iter 46): archaeology mode lifts ONLY the age-based
    # hiding — a dormant-but-true memory ("the client set the budget in March")
    # must be findable months later. The two INTEGRITY guards above (future
    # timestamp = tamper signal; valid_until hard-expire) hold in every mode.
    if ignore_age:
        return False
    age_days = (now - base) / 86400.0
    return is_stale(age_days, half_life_days)


def _topic_penalty_strength() -> float:
    """Strength of the off-topic recall penalty (verimem.topic_priors). Default 0.0
    (no-op) — wires the previously-dormant moat into the live recall WITHOUT changing
    default ranking; set ENGRAM_TOPIC_PENALTY=0.10 to down-rank lessons/* facts on
    task-style queries (the bench-v2 hard-negative fix). A/B on the live corpus before
    raising the default (the corpus, not LongMemEval, carries lessons/* topics)."""
    import os
    try:
        return max(0.0, min(1.0, float(os.environ.get("ENGRAM_TOPIC_PENALTY", "0.0"))))
    except (TypeError, ValueError):
        return 0.0


def _apply_topic_penalty_to_sims(sims, facts, query_text):
    """Down-rank broadly-matching off-topic facts (verimem.topic_priors) for task-style
    queries. No-op when the penalty is 0 or the query is meta-style. Fail-soft."""
    penalty = _topic_penalty_strength()
    if penalty <= 0.0:
        return sims
    try:
        from .topic_priors import apply_topic_penalty
        topics = []
        for f in facts:
            t = getattr(f, "topic", None)
            if t is None:
                try:  # sqlite3.Row / dict on the legacy SQL path
                    t = f["topic"]
                except (TypeError, KeyError, IndexError):
                    t = None
            topics.append(t)
        return apply_topic_penalty(sims, topics, query_text=query_text or "", penalty=penalty)
    except Exception:  # noqa: BLE001 — ranking nicety must never crash recall
        return sims


def _migrate_v0_to_v1(conn: sqlite3.Connection) -> None:
    """No-op: the pre-cycle-#78 schema is already created by _SCHEMA
    CREATE TABLE IF NOT EXISTS. This entry exists only to keep the
    migration ladder contiguous from v0 (fresh) through v3 (cycle #109)
    as required by ``ensure_schema_version``.
    """


def _migrate_v1_to_v2(conn: sqlite3.Connection) -> None:
    """Add supersession columns to facts table (cycle #78, 2026-05-16).

    Columns are nullable: existing rows behave as "live" (the default
    retrieval filter is ``WHERE superseded_by IS NULL``).
    """
    # SQLite ADD COLUMN is online + cheap; defaults to NULL.
    for col_ddl in (
        "ALTER TABLE facts ADD COLUMN superseded_by TEXT",
        "ALTER TABLE facts ADD COLUMN superseded_at REAL",
        "ALTER TABLE facts ADD COLUMN superseded_reason TEXT",
    ):
        try:
            conn.execute(col_ddl)
        except sqlite3.OperationalError as exc:
            # Fresh DB created by current _SCHEMA already has the columns —
            # the schema version table reads 0 on a brand-new file, so the
            # ladder still runs, and the ADD COLUMN fails with
            # "duplicate column name". Swallow that case only.
            if "duplicate column name" not in str(exc).lower():
                raise
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_facts_superseded_by "
        "ON facts(superseded_by)"
    )


def _migrate_v2_to_v3(conn: sqlite3.Connection) -> None:
    """Add provenance columns to facts table (cycle #109, 2026-05-16).

    Existing rows are marked ``status='legacy_unverified'`` to distinguish
    them from facts created post-fix with default ``status='model_claim'``.

    Note: in this branch's history the provenance schema lives at v3
    (not v2 as the original cycle #109 commit assumed) because PR #43
    landed the supersession columns as v2 first.
    """
    for col_ddl in (
        "ALTER TABLE facts ADD COLUMN verified_by TEXT NOT NULL DEFAULT '[]'",
        "ALTER TABLE facts ADD COLUMN status TEXT NOT NULL DEFAULT 'model_claim'",
        "ALTER TABLE facts ADD COLUMN source_signature TEXT",
    ):
        try:
            conn.execute(col_ddl)
        except sqlite3.OperationalError as exc:
            # Fresh DB created by current _SCHEMA already has the columns.
            # Swallow "duplicate column name" only.
            if "duplicate column name" not in str(exc).lower():
                raise

    # Mark all pre-existing rows as legacy_unverified.
    # Idempotent: future migration runs find no rows to update because
    # new rows post-migration use the explicit DEFAULT.
    conn.execute(
        "UPDATE facts SET status = 'legacy_unverified' "
        "WHERE status = 'model_claim' AND created_at < ?",
        (time.time(),),
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_facts_status ON facts(status)"
    )


def _migrate_v3_to_v4(conn: sqlite3.Connection) -> None:
    """Cycle #157 (2026-05-19): partial UNIQUE INDEX on auto-cluster-master
    facts for cross-process protection.

    Cycle 155 ``threading.Lock`` chiude la TOCTOU race intra-process.
    Cycle 156 opus design doc (raccomandazione A) ha definito il fix
    cross-process: partial UNIQUE INDEX su ``facts(topic) WHERE
    superseded_by IS NULL AND proposition LIKE 'AUTO-CLUSTER-MASTER%'``.

    Pre-step richiesto: marcare come superseded tutti i duplicati
    pre-existing (mantenendo il più vecchio come live). Altrimenti il
    ``CREATE UNIQUE INDEX`` fallisce su DB con duplicati pre-cycle 155.

    Pattern segue cycle 156 design doc §2.A.1 verbatim.
    """
    # Step 1 — pre-clean: marca duplicati extra come superseded_by =
    # oldest. Idempotente: run successive non trovano righe da updatare.
    conn.execute(
        "UPDATE facts SET "
        "  superseded_by = (SELECT MIN(id) FROM facts AS f2 "
        "                   WHERE f2.topic = facts.topic "
        "                     AND f2.superseded_by IS NULL "
        "                     AND f2.proposition LIKE 'AUTO-CLUSTER-MASTER%'), "
        "  superseded_at = ?, "
        "  superseded_reason = 'cycle157-unique-index-dedup' "
        "WHERE proposition LIKE 'AUTO-CLUSTER-MASTER%' "
        "  AND superseded_by IS NULL "
        "  AND id NOT IN ( "
        "    SELECT MIN(id) FROM facts "
        "    WHERE proposition LIKE 'AUTO-CLUSTER-MASTER%' "
        "      AND superseded_by IS NULL "
        "    GROUP BY topic"
        "  )",
        (time.time(),),
    )
    # Step 2 — create the partial UNIQUE INDEX. SQLite ≥ 3.8.0 supports
    # partial indexes (verified empirically cycle 156 = 3.51.1 on dev
    # env). Idempotent via IF NOT EXISTS.
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_facts_auto_master_unique "
        "ON facts(topic) "
        "WHERE superseded_by IS NULL "
        "  AND proposition LIKE 'AUTO-CLUSTER-MASTER%'",
    )


def _migrate_v4_to_v5(conn: sqlite3.Connection) -> None:
    """Cycle 160 (2026-05-19): pattern card schema. Add four optional
    metadata columns on facts. Empirical motivation: bench
    ``9379c8141a3e`` measured TPR@20 = 70% for semantic-only retrieval
    on production store (1391 facts). The residual 30% is the wording-
    mismatch class — fact exists, but embedding cosine fails to rank
    it in the top-k. The new columns let the host index explicitly:

      * ``trigger_keywords`` — comma-separated, short tokens beyond
        the proposition body (e.g. ``"AM-GM,pairing,factorial"``).
      * ``applicable_when`` — one-sentence condition.
      * ``worked_example`` — short paste-ready snippet.
      * ``lineage_to`` — comma-separated fact ids this fact extends
        / generalizes (technique inheritance, independent of cycle
        #78 supersession which is a row-level invalidation marker).

    Backward-compat: all four nullable / empty default. Pre-cycle-160
    callers see zero behaviour change.
    """
    for col_ddl in (
        "ALTER TABLE facts ADD COLUMN trigger_keywords TEXT",
        "ALTER TABLE facts ADD COLUMN applicable_when TEXT",
        "ALTER TABLE facts ADD COLUMN worked_example TEXT",
        "ALTER TABLE facts ADD COLUMN lineage_to TEXT",
    ):
        try:
            conn.execute(col_ddl)
        except sqlite3.OperationalError as exc:
            # Fresh DB created by current _SCHEMA already has the columns.
            if "duplicate column name" not in str(exc).lower():
                raise


def _migrate_v5_to_v6(conn: sqlite3.Connection) -> None:
    """Cycle 2026-05-27 round 12 (F-fix): provenance schema for trusted-
    hook bypass in anti_confab_gate.

    Background: master pre-compact facts (topic=handoff/pre-compact-*)
    were getting quarantined because L1.x retrospective-keyword detectors
    fired on SHIPPED/COMPLETO/AUTHORIZED/MONITORED/AUTOMATED — keywords
    naturally present in narrative recaps.

    Fix (GPT triangulation proposal F over Gemini D): provenance-based
    bypass NOT topic-based. Two new columns:

      * writer_role — 'system_hook' / 'trusted_hook' / 'user' /
        'agent_inference' (default). Not user-controllable for trusted
        values.
      * meta_narrative — 1 if the fact is a retrospective continuity
        snapshot, 0 if a prospective claim (default).

    Gate skips L1.x ONLY when both writer_role IN TRUSTED_HOOKS AND
    meta_narrative=1. Defense in depth: either alone is insufficient.

    Backward-compat: existing rows get the explicit defaults
    ('agent_inference', 0) — same behaviour as before this migration.
    """
    for col_ddl in (
        (
            "ALTER TABLE facts ADD COLUMN writer_role TEXT NOT NULL "
            "DEFAULT 'agent_inference'"
        ),
        (
            "ALTER TABLE facts ADD COLUMN meta_narrative INTEGER NOT NULL "
            "DEFAULT 0"
        ),
    ):
        try:
            conn.execute(col_ddl)
        except sqlite3.OperationalError as exc:
            # Fresh DB created by current _SCHEMA already has the columns.
            if "duplicate column name" not in str(exc).lower():
                raise
    # Cheap index for future filtering queries.
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_facts_writer_role "
        "ON facts(writer_role)"
    )


def _migrate_v6_to_v7(conn: sqlite3.Connection) -> None:
    """Cycle 2026-05-27 round 13 P0c: transactional rollback for destructive
    operations (forget / supersede / modify) via facts_undo_log.

    Aurelio audit gap C5: senza rollback, ogni forget e potenziale data loss.
    Triangulation Gemini+GPT consensus: P0 priority, foundation safety.

    Schema:
        facts_undo_log(op_id, op_type, fact_id, pre_row_json, created_at,
                       undone_at, ttl_expires_at)

    TTL 7 giorni: la riga fact stessa non e' impattata dall'undo log TTL;
    e' un audit/recovery trail bounded.
    """
    from .undo_log import ensure_undo_table
    ensure_undo_table(conn)


def _migrate_v7_to_v8(conn: sqlite3.Connection) -> None:
    """2026-06-03 buco #3 (validita temporale): colonna ``last_verified_at``.

    Un capability-claim verificato e mai smentito restava live nel recall
    per sempre (lo schema non aveva ne ``last_verified_at`` ne ``expires_at``)
    -> caso A2A "prima funzionava" (freshness.py:3-5). Questa colonna da' al
    recall l'eta-da-ultima-verifica su cui ``freshness.is_stale`` declassa.

    Additiva, zero-rischio. SQLite ADD COLUMN non ammette ``DEFAULT
    <colonna>``, quindi la colonna e' nullable e le righe esistenti sono
    backfillate a ``created_at`` (= "verificato quando creato", il contratto
    di default che store() impone d'ora in poi sui fatti nuovi).
    """
    try:
        conn.execute("ALTER TABLE facts ADD COLUMN last_verified_at REAL")
    except sqlite3.OperationalError as exc:
        # Fresh DB created by current _SCHEMA already has the column.
        if "duplicate column name" not in str(exc).lower():
            raise
    # Backfill: i fatti pre-v8 sono "verificati quando creati".
    conn.execute(
        "UPDATE facts SET last_verified_at = created_at "
        "WHERE last_verified_at IS NULL"
    )


def _migrate_v8_to_v9(conn: sqlite3.Connection) -> None:
    """2026-06-03 buco silent-poisoning (Sorella C): colonna ``embedding_model``.

    Il recall pre-v9 filtrava solo ``length(embedding) = 1536`` -> un vettore
    di un MODELLO diverso ma STESSA dim passava il filtro e inquinava il corpus
    (cosine cross-spazio = rumore). Questa colonna registra per-riga il modello
    che ha prodotto il vettore, cosi' il recall isola lo spazio attivo.

    Additiva, zero-rischio. Nullable: le righe pre-v9 restano NULL e il recall
    le tratta come ``_LEGACY_EMBEDDING_MODEL`` via COALESCE (erano tutte
    all-MiniLM-L6-v2, l'unico modello storico). NESSUN backfill con un valore
    inventato: NULL == "non stampato, assumi baseline" e' il contratto fail-safe
    (come last_verified_at in v8). Le scritture nuove sono stampate da store().
    """
    try:
        conn.execute("ALTER TABLE facts ADD COLUMN embedding_model TEXT")
    except sqlite3.OperationalError as exc:
        # Fresh DB created by current _SCHEMA already has the column.
        if "duplicate column name" not in str(exc).lower():
            raise


def _migrate_v9_to_v10(conn: sqlite3.Connection) -> None:
    """2026-06-14 valid-time bi-temporale: colonna ``valid_until``.

    Pre-v10 un fatto restava recall-abile finche' non superseduto o scaduto
    per ETA (last_verified_at oltre half-life, v8). Mancava il VALID-TIME: il
    momento oltre cui il fatto smette di essere vero per natura — es. "il
    deploy e' in corso", "la incident review e' aperta", "il feature-flag X e'
    ON fino al rollout": informazione con una scadenza intrinseca, non un
    decadimento graduale. ``valid_until`` da' al recall un hard-expire:
    ``valid_until <= now`` => escluso, a prescindere dall'eta.

    Additiva, zero-rischio. Nullable, NESSUN backfill: NULL == "nessuna
    scadenza" e' il contratto fail-safe (i fatti esistenti non scadono, recall
    byte-identico finche' nessuna scrittura setta il campo). Le scritture che
    vogliono una scadenza la passano via store(); il default resta None.
    Differenziatore bi-temporale vs Mem0/Zep.
    """
    try:
        conn.execute("ALTER TABLE facts ADD COLUMN valid_until REAL")
    except sqlite3.OperationalError as exc:
        # Fresh DB created by current _SCHEMA already has the column.
        if "duplicate column name" not in str(exc).lower():
            raise


def _migrate_v10_to_v11(conn: sqlite3.Connection) -> None:
    """2026-06-19 typed LOGICAL-derivation edge ``derives_from`` (ATMS depends_on).

    R26 verified that ``lineage_to`` is a NARRATIVE/session-successor pointer (95%
    cross-topic ``--lineage-to auto`` chain links), not a logical-derivation edge, so it
    must not feed the truth-maintenance cascade. This adds the missing typed edge: the ids
    of the facts whose TRUTH justifies this one. When such a parent is superseded/
    contradicted, ``justified_memory.propagate`` retracts this fact transitively. Additiva,
    nullable, NO backfill (existing facts have none → propagate stays dormant until the
    write-path populates it). Fail-safe: recall byte-identical (column unused by recall).
    """
    try:
        conn.execute("ALTER TABLE facts ADD COLUMN derives_from TEXT")
    except sqlite3.OperationalError as exc:
        if "duplicate column name" not in str(exc).lower():
            raise


def _migrate_v11_to_v12(conn: sqlite3.Connection) -> None:
    """2026-06-20 persist the write-time grounding score (moonshot #1).

    The anti-confab gate computes an L4 source⊢fact entailment score (grounding_gate,
    AUROC 0.971) then discarded it after the pass/fail decision. Persist it on the fact
    so retrieval/answering can condition on a write-time trust coordinate no competitor
    has. Additive, nullable, NO backfill (existing facts → None until re-stored under
    ENGRAM_GROUNDING_WRITE). Fail-safe: recall byte-identical (column unused by recall).
    """
    try:
        conn.execute("ALTER TABLE facts ADD COLUMN grounding_score REAL")
    except sqlite3.OperationalError as exc:
        if "duplicate column name" not in str(exc).lower():
            raise


def _migrate_v12_to_v13(conn: sqlite3.Connection) -> None:
    """2026-07-05 bi-temporal EVENT time ``asserted_at`` (valid-FROM).

    Root-cause (loop iter 42): the semantic time was being stuffed into
    ``created_at``, so the staleness half-life hid backdated-but-current facts
    and the anti-spoof fail-closed guard hid future-dated ones (measured: 83%
    of a timestamped HaluMem store invisible to recall). ``created_at`` stays
    TRANSACTION time (never backdated — the freshness/anti-spoof guards keep
    their soundness); ``asserted_at`` is WHEN IT WAS SAID/TRUE — it drives the
    reconcile age-gap and answer-with-history, and a future value is legitimate
    (calendar facts), never spoofing. Additive, nullable, NO backfill: NULL =
    "event time unknown" → callers fall back to created_at. Recall
    byte-identical (column unused by the recall filters).
    """
    try:
        conn.execute("ALTER TABLE facts ADD COLUMN asserted_at REAL")
    except sqlite3.OperationalError as exc:
        if "duplicate column name" not in str(exc).lower():
            raise


def _migrate_v14_to_v15(conn: sqlite3.Connection) -> None:
    """v15 (2026-07-19): persist the write-time confidence_tier. Additive,
    nullable, no backfill (existing rows -> None until re-stored)."""
    try:
        conn.execute("ALTER TABLE facts ADD COLUMN confidence_tier TEXT")
    except sqlite3.OperationalError as exc:
        if "duplicate column name" not in str(exc).lower():
            raise


def _migrate_v13_to_v14(conn: sqlite3.Connection) -> None:
    """2026-07-13 epistemic label (cortex transfer #1).

    The GUARANTEE kind of a fact — proven(proof) / unbeaten(bound) /
    refuted(counterexample) — orthogonal to provenance ``status``. Motivated by
    the lab case coprime6→deficient: holds to 10^6, dies at 5391411025 —
    "unbeaten" and "proven" must never be conflated, and the composition layer
    must only build from labels it can trust. Additive, nullable, NO backfill:
    NULL = unlabeled (every ordinary fact). Recall byte-identical (column
    unused by recall filters); transitions enforced by ``set_epistemic``.
    """
    try:
        conn.execute("ALTER TABLE facts ADD COLUMN epistemic TEXT")
    except sqlite3.OperationalError as exc:
        if "duplicate column name" not in str(exc).lower():
            raise


@dataclass
class Fact:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    proposition: str = ""
    topic: str = ""
    confidence: float = 0.5
    source_episodes: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    # Cycle #78 supersession (nullable: live fact == all three None).
    superseded_by: str | None = None
    superseded_at: float | None = None
    superseded_reason: str | None = None
    # Cycle #109 provenance fields (schema v3).
    verified_by: list[str] = field(default_factory=list)
    status: str = "model_claim"
    source_signature: str | None = None
    # Cycle 160 (2026-05-19) pattern card schema v5 — optional structured
    # metadata for high-precision retrieval. Empirical motivation: bench
    # 9379c8141a3e shows TPR@20=70% on semantic-only recall; the 30% miss
    # is wording-mismatch. trigger_keywords / applicable_when match those
    # cases; worked_example carries a paste-ready snippet; lineage_to
    # records the technique-inheritance graph independent of supersession.
    trigger_keywords: list[str] = field(default_factory=list)
    applicable_when: str | None = None
    worked_example: str | None = None
    lineage_to: list[str] = field(default_factory=list)
    # Cycle 2026-05-27 round 12 F-fix provenance schema v6.
    # writer_role distinguishes 'system_hook' / 'trusted_hook' / 'user' /
    # 'agent_inference' for the anti-confab gate's trusted-hook bypass.
    # meta_narrative marks retrospective continuity snapshots (recap-of-
    # what-was-done) that should not be evaluated as prospective claims.
    # Both required together (defense in depth) to skip the verified_by
    # hard-gate AND the L1.x detectors.
    writer_role: str = "agent_inference"
    meta_narrative: bool = False
    # v8 (2026-06-03) buco #3: timestamp dell'ultima verifica. None ==
    # "non settato" -> store() e _row lo trattano come == created_at
    # (il fatto e' verificato quando creato). Appeso in coda al dataclass
    # per non spostare l'ordine posizionale dei campi pre-v8.
    last_verified_at: float | None = None
    # v10 (2026-06-14) valid-time bi-temporale: istante oltre cui il fatto non
    # e' piu' valido (hard-expire nel recall, indipendente dall'eta/decay).
    # None == nessuna scadenza (default). Appeso in coda per non spostare
    # l'ordine posizionale dei campi pre-v10.
    valid_until: float | None = None
    # v11 (2026-06-19) typed LOGICAL-derivation edge (ATMS depends_on): ids of the
    # facts whose TRUTH justifies this one. DISTINCT from the narrative lineage_to
    # (R26). justified_memory.fact_to_belief reads THIS as depends_on; propagate
    # retracts this fact when a derives_from parent loses justification. Default
    # empty => propagate dormant until the write-path declares derivations.
    derives_from: list[str] = field(default_factory=list)
    # v12 (2026-06-20) write-time grounding score (0-100): the L4 source⊢fact
    # entailment score (grounding_gate, AUROC 0.971) computed by the anti-confab gate
    # and now PERSISTED (it was discarded). A write-time trust coordinate no competitor
    # has; enables provenance-conditioned retrieval/answering (docs/MOONSHOTS.md #1).
    # None == not computed (no source / ENGRAM_GROUNDING_WRITE off). Appended last;
    # recall byte-identical (column unused by recall until conditioning ships).
    grounding_score: float | None = None
    #: v15 (2026-07-19) write-time confidence tier (high/borderline/low/
    #: unverified) - the judge's CONFIDENCE band, persisted for recall/audit.
    #: None on pre-v15 rows / when no judge ran.
    confidence_tier: str | None = None
    # v13 (2026-07-05) bi-temporal EVENT time (valid-FROM): when the fact was
    # said/true, DISTINCT from created_at (transaction time, never backdated so
    # the freshness/anti-spoof guards stay sound). Drives the reconcile age-gap
    # and answer-with-history; a FUTURE value is legitimate (calendar facts).
    # None == event time unknown -> callers fall back to created_at.
    asserted_at: float | None = None
    # v14 (2026-07-13) epistemic label (cortex transfer #1): the GUARANTEE kind,
    # orthogonal to provenance ``status`` — {"kind": "proven"|"unbeaten"|
    # "refuted", ...} per engram/epistemic.py (monotone transitions enforced by
    # set_epistemic, refuted absorbing). None == unlabeled (every ordinary
    # fact). The composition layer builds only from labels it can trust.
    epistemic: dict | None = None


# ── P0.3 (2026-06-09) — stage-2 cross-encoder rerank, default ON 2026-06-10 ──
# Verified on a COPY of the live corpus, twice, paired McNemar:
#   HARD n=300 (scripts/bench_rerank_n300_fast.py): R@1 0.520 -> 0.810
#   (b=10/c=97, chi2=69.12, p<1e-5), MRR 0.611 -> 0.832, ~1.6s/probe CPU.
#   FAIR n=120 fluent paraphrases (scripts/bench_rerank_fair.py): R@1
#   0.533 -> 0.683 p=0.00052, R@10 0.750 -> 0.817 p=0.013 — survives the
#   regime that REFUTED recall_hybrid, hence the default flip.
# Opt-out: ENGRAM_RECALL_RERANK=0 (or off/false/no) = byte-identical legacy
# ranking; latency knob: ENGRAM_RERANK_TOPN (pairs scored, default 20).
# The default model is the FAST winner; bge-reranker-v2-m3 measured
# ~30s/probe on CPU — do NOT default to it.
_DEFAULT_RERANK_MODEL = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
_RERANKER = None
_RERANKER_LOCK = threading.Lock()


def _rerank_enabled() -> bool:
    """Default ON (flip 2026-06-10). Only an explicit opt-out disables."""
    return os.environ.get("ENGRAM_RECALL_RERANK", "").strip().lower() not in (
        "0", "off", "false", "no",
    )


def _topk_deterministic(sims, n: int, facts):
    """Top-``n`` candidate indices by ``(-score, fact.id)`` — deterministic and
    ROW-ORDER INVARIANT: any permutation of the same candidate rows (full corpus
    vs ANN pool) yields the same fact sequence. Replaces the bare
    ``np.argsort(-sims)[:n]`` whose tie order was quicksort-arbitrary and made
    ANN-on recall score-identical but not byte-identical (iter 23, mandate).

    Cost: O(N) argpartition + a Python sort over ~n candidates (plus the boundary
    tie-group) — asymptotically cheaper than the full argsort it replaces."""
    m = int(len(sims))
    if m == 0 or n <= 0:
        return np.array([], dtype=int)
    if n < m:
        part = np.argpartition(-sims, n - 1)[:n]
        boundary = float(sims[part].min())
        cand = np.nonzero(sims >= boundary)[0]
    else:
        cand = np.arange(m)
    def _fid(obj) -> str:
        fid = getattr(obj, "id", None)
        if fid is None:
            try:                      # sqlite Row on the legacy path (SCAN-68:
                fid = obj["id"]       # cache-vs-legacy must stay symmetric)
            except Exception:  # noqa: BLE001
                fid = ""
        return str(fid or "")

    order = sorted(cand.tolist(), key=lambda i: (-float(sims[i]), _fid(facts[i])))
    return np.asarray(order[:n], dtype=int)


def _ann_recall_enabled() -> bool:
    """ANN pre-narrowing of the recall corpus. Default AUTO-ON (iter 26 flip,
    mandate 2026-07-04): enabled when faiss is importable. Safe as a default
    because (a) the _ANN_MIN_N=100k gate keeps it dormant on small corpora,
    (b) results are byte-identical to brute WHENEVER the HNSW pool contains the
    true top-k — deterministic tie-break (iter 23) removes all order divergence,
    and recall-in-pool measures ~1.0 on real e5 at oversample 8; but HNSW is
    APPROXIMATE, so above the gate a borderline fact can rarely miss the pool
    (critic 2026-07-05 corrected the earlier unconditional "byte-identical"),
    (c) the background build keeps the hot path exact-brute until the index is
    ready — no synchronous build stall, and a version mismatch never serves a
    stale index. ENGRAM_ANN_RECALL=0 opts out (exact at any scale); =1 forces on."""
    v = os.environ.get("ENGRAM_ANN_RECALL", "").strip().lower()
    if v in ("0", "off", "false", "no"):
        return False
    if v in ("1", "on", "true", "yes"):
        return True
    from verimem.ann_index import faiss as _faiss
    return _faiss is not None


def _entity_live_enabled() -> bool:
    """Entity-live write path (2026-06-10): keep the entity KG in sync at
    write time so PPR coverage doesn't decay between backfills. Default ON;
    ENGRAM_ENTITY_LIVE=0 opts out."""
    return os.environ.get("ENGRAM_ENTITY_LIVE", "").strip().lower() not in (
        "0", "off", "false", "no",
    )


def _reconcile_on_write_enabled() -> bool:
    """P1 truth-reconciliation on write (2026-06-17): after a fact is
    entity-linked, find shared-entity update candidates and reconcile. Default
    OFF (opt-in) until the false-supersede rate is measured on a real corpus;
    ENGRAM_RECONCILE_ON_WRITE=1 turns it on (fail-safe: contests, never
    auto-supersedes)."""
    return os.environ.get("ENGRAM_RECONCILE_ON_WRITE", "").strip().lower() in (
        "1", "on", "true", "yes",
    )


def _source_auto_confirm_enabled() -> bool:
    """Auto-confirmation on write (2026-07-11): when a fact restates the SAME
    proposition as live same-topic facts from OTHER sources, feed the source-trust
    consistency channel (independence-aware acceptance, so a write-majority cartel
    cannot self-confirm — validated on the real gate path, benchmark/
    independence_validation.py). Default OFF; ENGRAM_SOURCE_AUTO_CONFIRM=1 turns it on.
    Only the consistency channel is touched — never outcome (temporal supersession is
    the world moving, not a source lying: the reverted #20b attribution error)."""
    return os.environ.get("ENGRAM_SOURCE_AUTO_CONFIRM", "").strip().lower() in (
        "1", "on", "true", "yes",
    )


def _reconcile_auto_supersede_enabled() -> bool:
    """Allow reconcile-on-write to SUPERSEDE (apply a knowledge update), not just
    contest. Default OFF (fail-safe, unchanged): every conflict is only contested.
    ENGRAM_RECONCILE_AUTO_SUPERSEDE=1 lets a clean temporal update actually apply
    — required to move the HaluMem *Updating* slice. Composed with the evidence
    gate below so it can never become sycophantic by accident."""
    return os.environ.get("ENGRAM_RECONCILE_AUTO_SUPERSEDE", "").strip().lower() in (
        "1", "on", "true", "yes",
    )


def _reconcile_evidence_policy(auto_supersede: bool) -> tuple[bool, bool]:
    """Anti-sycophancy policy for write-path supersede -> ``(strict, tiered)``.

    strict = require evidence to supersede ANY fact (max safety, but kills bare
    update-recall — measured 0.28->0 on HaluMem, whose updates are bare claims).
    tiered = require evidence only to overwrite an EVIDENCED fact; a bare->bare
    update still applies (recall preserved). When auto-supersede is on the DEFAULT
    is tiered (iter-3 finding: protect verified truth without the recall cliff).
    ENGRAM_RECONCILE_REQUIRE_EVIDENCE=1 -> strict; =0 -> neither (raw recency+
    authority, sycophantic). No auto-supersede -> (False, False)."""
    if not auto_supersede:
        return (False, False)
    v = os.environ.get("ENGRAM_RECONCILE_REQUIRE_EVIDENCE", "").strip().lower()
    if v in ("1", "on", "true", "yes"):
        return (True, False)      # strict
    if v in ("0", "off", "false", "no"):
        return (False, False)     # none (explicit opt-out of all protection)
    return (False, True)          # default: tiered


def _rerank_topn() -> int:
    """CE pool size = pairs actually scored — the latency knob (20 ≈ 1.6s/q
    CPU). Read per-call (like the centering flag) so tests/A-B can flip it."""
    try:
        return max(1, int(os.environ.get("ENGRAM_RERANK_TOPN", "20")))
    except ValueError:
        return 20


def _rerank_max_doc_chars() -> int:
    """Length guard for stage-2 rerank. The mmarco CE truncates at 512
    tokens; on documents longer than its window it scores only the head and
    SCRAMBLES an already-good bi-encoder order (comparative LongMemEval n=100
    2026-06-10: rerank recall@5 0.723 vs 0.800 base on long session docs,
    while HARD n=300 + FAIR n=120 on SHORT facts both showed a clear win).
    When the candidate pool's MEDIAN proposition exceeds this many chars the
    CE is skipped entirely (not even loaded). Default 2000 (~512 tokens);
    ENGRAM_RERANK_MAX_DOC_CHARS=0 disables the guard (force CE always)."""
    try:
        return max(0, int(os.environ.get("ENGRAM_RERANK_MAX_DOC_CHARS", "2000")))
    except ValueError:
        return 2000


def _load_reranker():
    """Process-wide lazy CrossEncoder scorer (mirror of embedding._load_model).

    Cache-only load first; network retry ONLY when no offline flag is set —
    a network stall under the lock must never wedge recall (the 2026-06-05
    embedding-hang lesson). CPU pinned: the 8GB GPU OOMs with the e5 encoder
    and the CE resident together.
    """
    global _RERANKER
    if _RERANKER is None:
        with _RERANKER_LOCK:
            if _RERANKER is None:
                from sentence_transformers import CrossEncoder
                model = os.environ.get(
                    "ENGRAM_RERANK_MODEL", _DEFAULT_RERANK_MODEL,
                ).strip() or _DEFAULT_RERANK_MODEL
                try:
                    _RERANKER = CrossEncoder(
                        model, max_length=512, device="cpu",
                        local_files_only=True,
                    )
                except Exception:  # noqa: BLE001 — any load error → online retry/raise
                    if embedding._offline():
                        raise
                    _RERANKER = CrossEncoder(
                        model, max_length=512, device="cpu",
                    )
    m = _RERANKER
    return lambda pairs: [
        float(s) for s in m.predict(pairs, show_progress_bar=False)
    ]


def _reranker_ready() -> bool:
    """True once the CE is resident in this process — a None check (no lock, no
    load), so the rerank hot path can decide in nanoseconds whether the model is
    still cold."""
    return _RERANKER is not None


# --- Rerank circuit-breaker (task #16, 2026-07-10) ---------------------------
# Observed on the external read-path runs: on a loaded CPU the CE predict
# exceeds the budget on EVERY query — each recall then pays the full budget in
# wasted wall-clock and keeps bi-encoder order anyway. Systematic overruns are
# a session property, not per-query bad luck: after N CONSECUTIVE overruns the
# CE is disabled for this process (explicit log, one line) and recall stops
# waiting. A successful in-budget rerank resets the count, so transient
# contention never disables the measured R@1 lift permanently.
_RERANK_BREAKER: dict[str, Any] = {"consecutive": 0, "tripped": False, "cold": 0}


def _rerank_breaker_n() -> int:
    """Consecutive overruns that trip the breaker. 0 disables the breaker.
    Env ENGRAM_RERANK_BREAKER_N, default 5."""
    try:
        return max(0, int(os.environ.get("ENGRAM_RERANK_BREAKER_N", "5")))
    except ValueError:
        return 5


def _rerank_cold_breaker_n() -> int:
    """Cold-load overruns tolerated before tripping (0 disables). F1 C1
    (2026-07-10): a cold overrun is transient by definition — the CE is still
    warming — so it must NOT count toward the steady trip (the first burst of
    queries of any fresh process was disabling the rerank, worth +0.29 R@1,
    for the whole session). This separate, much more generous bound only
    covers the pathological never-warms case (broken CE install): each cold
    overrun costs the small cold budget (~0.25s), so 40 ≈ 10s total waste.
    Env ENGRAM_RERANK_COLD_BREAKER_N, default 40."""
    try:
        return max(0, int(os.environ.get("ENGRAM_RERANK_COLD_BREAKER_N", "40")))
    except ValueError:
        return 40


def _rerank_breaker_reset() -> None:
    """Re-arm the breaker (tests; model/env swap at runtime)."""
    _RERANK_BREAKER["consecutive"] = 0
    _RERANK_BREAKER["tripped"] = False
    _RERANK_BREAKER["cold"] = 0


def _rerank_breaker_overrun() -> None:
    _RERANK_BREAKER["consecutive"] += 1
    n = _rerank_breaker_n()
    if n and not _RERANK_BREAKER["tripped"] \
            and _RERANK_BREAKER["consecutive"] >= n:
        _RERANK_BREAKER["tripped"] = True
        _LOG.warning(
            "rerank breaker TRIPPED after %d consecutive budget overruns — "
            "CE rerank disabled for this process (bi-encoder order stands; "
            "restart or _rerank_breaker_reset() to re-arm)", n,
        )


def _rerank_breaker_cold_overrun() -> None:
    _RERANK_BREAKER["cold"] = _RERANK_BREAKER.get("cold", 0) + 1
    n = _rerank_cold_breaker_n()
    if n and not _RERANK_BREAKER["tripped"] \
            and _RERANK_BREAKER["cold"] >= n:
        _RERANK_BREAKER["tripped"] = True
        _LOG.warning(
            "rerank breaker TRIPPED after %d cold-load overruns — the CE never "
            "became resident (broken install / perpetual load?); rerank "
            "disabled for this process", n,
        )


def _rerank_cold_budget_s() -> float:
    """Wall-clock budget for a rerank attempt while the CE is still COLD-loading.
    Much smaller than the steady budget: a cold query must not pay the full ~3s
    before degrading (measured recall p95 3.1s tail, 2026-06-14). The load keeps
    running in the daemon worker, so a later query — once the CE is resident —
    reranks with the full budget. Env override ENGRAM_RERANK_COLD_BUDGET_S;
    default 0.25s."""
    try:
        return max(0.0, float(os.environ.get("ENGRAM_RERANK_COLD_BUDGET_S", "0.25")))
    except ValueError:
        return 0.25


def _ppr_fusion_budget_s() -> float:
    """Wall-clock budget for the opt-in PPR+BM25 fusion (default-ON prereq #1,
    audit round-2 2026-06-14). The entity-PPR power iteration (nx.pagerank
    max_iter=200 over the full-corpus graph) is the only UNCAPPED cost on the
    recall ON-path — the CE-rerank is already budgeted (_rerank_stage2). Under
    CPU contention it is the same hang failure-mode the rerank was fixed for, so
    promoting fusion to default-ON without this guard would expose recall to an
    unbounded tail the default-OFF path does not have. On overrun the fusion is
    skipped and the already-reranked hits are kept. Env
    ENGRAM_PPR_FUSION_BUDGET_S; default 2.0s — generous on purpose: the cap exists
    to kill the PATHOLOGICAL hang (the 10-min failure-mode), NOT to trim the p95,
    so it must clear the legitimate cold graph-build on the first ON-recall
    (measured to exceed 0.15s); steady-state (warm graph) PPR is sub-50ms, well
    under it. The #3 micro-bench will tune it on real cold/warm data. 0 = no cap."""
    try:
        return max(0.0, float(os.environ.get("ENGRAM_PPR_FUSION_BUDGET_S", "2.0")))
    except ValueError:
        return 2.0


def _ppr_fusion_enabled() -> bool:
    """DEFAULT-ON (2026-06-15): the 3-signal fusion (dense-cosine + entity-PPR +
    BM25-lexical + CE-rerank) is the retrieval moat — measured +7.5pp recall@5 on
    LongMemEval-s (n=300) at a +40ms steady-state cost (scripts/bench_fusion_
    latency.py). Made safe as a default by 3 prereqs: the PPR runs under a
    wall-clock budget (_ppr_fusion_budget_s — no hang), ALL recall paths
    (cache/legacy/cold) apply it (no cache-vs-cold asymmetry), and the corpus-floor
    (ENGRAM_PPR_FUSION_FLOOR, default 50) skips it on small corpora where it is
    pure overhead. Set ENGRAM_PPR_FUSION=0/off/false/no to opt OUT (back to pure
    cosine + CE-rerank, byte-identical to the pre-2026-06-15 default)."""
    return os.environ.get("ENGRAM_PPR_FUSION", "on").strip().lower() not in (
        "0", "off", "false", "no",
    )


class SemanticMemory:
    def __init__(
        self,
        db_path: Path | None = None,
        *,
        repo_root: Path | None = None,
    ) -> None:
        """Open / create the semantic-memory SQLite DB.

        Args:
            db_path: path to the SQLite file. Defaults to ``CONFIG.semantic_db``.
            repo_root: filesystem root used by the cycle #111 v2 verified_by
                hard-gate to verify ``file:<path>:<lineno>`` and ``commit <sha>``
                provenance refs. When ``None`` (default), the gate cannot
                perform I/O verification and DEMOTES every ``status='verified'``
                write to ``status='model_claim'`` — paranoid default. Pass the
                project repo root (e.g. ``Path(__file__).resolve().parent.parent``
                in production wire-up) to enable real verification.
        """
        self.db_path = db_path or CONFIG.semantic_db
        self.repo_root = Path(repo_root).resolve() if repo_root else None
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(_SCHEMA)
            from .migrations import ensure_schema_version
            ensure_schema_version(
                conn, db_id="semantic", target_version=_SEMANTIC_TARGET_VERSION,
                migrations=[
                    (1, _migrate_v0_to_v1),
                    (2, _migrate_v1_to_v2),
                    (3, _migrate_v2_to_v3),
                    (4, _migrate_v3_to_v4),
                    (5, _migrate_v4_to_v5),
                    (6, _migrate_v5_to_v6),
                    (7, _migrate_v6_to_v7),
                    (8, _migrate_v7_to_v8),
                    (9, _migrate_v8_to_v9),
                    (10, _migrate_v9_to_v10),
                    (11, _migrate_v10_to_v11),
                    (12, _migrate_v11_to_v12),
                    (13, _migrate_v12_to_v13),
                    (14, _migrate_v13_to_v14),
                    (15, _migrate_v14_to_v15),
                ],
            )
        # Cycle #135 (2026-05-17): hot-path recall cache. The default
        # recall(topic=None) used to do np.stack([deserialize(r)]) on
        # every row on every call — O(N) Python per query. We now hold
        # the full corpus (facts + stacked embedding matrix) in memory
        # and invalidate on store/delete. Lookup becomes
        # cosine(q_emb, matrix) — one BLAS dot product, O(1) Python.
        #
        # Aurelio direttiva 2026-05-17 sera: "ci interessa che HippoAgent
        # funzioni realmente e bene". Misura empirica laptop: p50(2k)
        # = 19.2ms, ratio p50(2k)/p50(500) = 3.08× linear scaling.
        # Post-cache target: ratio < 1.5× (only SQL fetchall scales).
        self._corpus_cache: dict[str, Any] | None = None
        self._cache_version: int = 0
        # ANN index cache for scale recall (auto-on when faiss is importable,
        # ENGRAM_ANN_RECALL=0 opts out — see _ann_recall_enabled; keyed by
        # _cache_version so a write invalidates/rebuilds it). Dormant until
        # the corpus crosses the gate; the exact brute-force path is unchanged.
        from verimem.ann_cache import ANNCache
        self._ann_cache = ANNCache()
        # Cross-process cache-coherence (sorelle loop 2026-06-03): a LONG-LIVED
        # probe connection whose ``PRAGMA data_version`` tracks commits made by
        # OTHER connections/processes. A fresh connection cannot do this — its
        # data_version is connection-relative and resets to a baseline on open
        # (verified empirically), so only a persistent connection sees the delta.
        self._dv_conn: sqlite3.Connection | None = None
        self._dv_lock = threading.Lock()
        # Serializza validate+build+swap della recall-cache: rende ATOMICO il
        # ramo cache-hit (niente torn-read: la tripla facts/matrix/lv proviene
        # da un UNICO snapshot) e impedisce rebuild concorrenti out-of-order su
        # istanza condivisa. Ordine lock SEMPRE _cache_lock -> _dv_lock (mai
        # inverso) => niente deadlock. Hit-path tiene il lock pochi us.
        self._cache_lock = threading.Lock()
        # Lazy entity store for the opt-in PPR-fusion recall path (step 2b).
        self._recall_es: Any = None
        # Incident 2026-06-10: replay deferred writes orphaned by a kill
        # (see _replay_pending_facts). Best-effort — must never break init.
        try:
            _replay_pending_facts(self)
        except Exception:  # noqa: BLE001 — a corrupt journal must not brick the db
            _LOG.warning("pending-facts replay failed at init", exc_info=True)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        # CVE-012 / CQ #11 fix: WAL + busy_timeout for concurrent writers.
        _t0 = time.monotonic()
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA busy_timeout=60000;")
            from verimem._sqlite_pragma import synchronous_mode
            conn.execute(f"PRAGMA synchronous={synchronous_mode()};")
        except sqlite3.OperationalError:
            pass
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()
            # Long-writer hunt 2026-06-10: name every long-held connection —
            # a WRITE held this long is what starves every other client.
            _dt = time.monotonic() - _t0
            if _dt > _slow_txn_warn_s():
                _LOG.warning(
                    "slow sqlite txn: %.2fs on %s (pid %d)",
                    _dt, self.db_path, os.getpid(),
                )

    def _db_data_version(self) -> int:
        """Cross-process cache-coherence probe (sorelle loop 2026-06-03).

        Returns SQLite ``PRAGMA data_version`` read on the instance's
        LONG-LIVED probe connection (lazily opened). That value is
        unchanged for commits made on this same connection, but CHANGES
        whenever any *other* connection — another thread or another
        process — commits to the file. That is exactly the signal the
        in-memory ``_cache_version`` counter (same-instance only) misses.

        Why persistent and not a fresh connection: a fresh connection's
        data_version is connection-relative and resets to a baseline on
        open, so two fresh probes never differ even across external
        writes (verified empirically). Only a persistent connection
        observes the delta. The probe issues PRAGMA only (never DML), so
        it stays in autocommit and never holds a read transaction open —
        no WAL-checkpoint starvation. ``check_same_thread=False`` + a lock
        make the shared read safe across threads.

        On any sqlite error the probe connection is dropped (recreated
        next call) and ``-1`` is returned: a sentinel that never equals a
        stored data_version → forces a rebuild (paranoid: never serve a
        possibly-stale cache when freshness cannot be verified).
        """
        with self._dv_lock:
            try:
                if self._dv_conn is None:
                    self._dv_conn = sqlite3.connect(
                        self.db_path, timeout=10.0, check_same_thread=False,
                    )
                return int(
                    self._dv_conn.execute(
                        "PRAGMA data_version"
                    ).fetchone()[0]
                )
            except sqlite3.Error:
                try:
                    if self._dv_conn is not None:
                        self._dv_conn.close()
                except sqlite3.Error:
                    pass
                self._dv_conn = None
                return -1

    def _store_telemetry(self, fact: Fact) -> None:
        """Admission-gate (opt-in): persist a telemetry-topic fact in a SEPARATE
        ``telemetry`` table instead of the curated ``facts`` table. Non-lossy —
        the event is preserved, just kept OUT of the curated corpus + recall.
        Lazy CREATE so the table only exists once the gate routes something."""
        with self._connect() as conn:  # contextmanager: auto-commit + close
            conn.execute(
                "CREATE TABLE IF NOT EXISTS telemetry ("
                "id TEXT PRIMARY KEY, topic TEXT, proposition TEXT, "
                "created_at REAL, writer_role TEXT)"
            )
            conn.execute(
                "INSERT OR REPLACE INTO telemetry(id, topic, proposition, "
                "created_at, writer_role) VALUES(?,?,?,?,?)",
                (fact.id, fact.topic, fact.proposition, fact.created_at,
                 getattr(fact, "writer_role", "agent_inference")),
            )

    def store(
        self, fact: Fact, *, return_replaced: bool = False,
        coherence_hook: Callable[[Fact, SemanticMemory], None] | None = None,
        hook_token: str | None = None,
        embed: str = "sync",
    ) -> bool | None:
        """Insert or replace a fact. Backwards-compatible default returns None.

        Cycle #109: validates ``fact.status`` against ``_VALID_STATUSES``.
        Serializes ``verified_by`` (list[str]) as JSON in SQL.

        Args:
            fact: the Fact instance to persist.
            return_replaced: opt-in observability flag (cycle #46, 2026-05-14).
                When True, returns a bool indicating whether a row with the
                same id ALREADY EXISTED before this write (i.e., the call
                overwrote a prior fact). When False (default), returns None
                for backwards compatibility with every existing caller.

        Returns:
            None when return_replaced=False (default, backwards compatible).
            bool when return_replaced=True: True if a pre-existing row was
            overwritten, False if it was a fresh insert.

        Raises:
            ValueError: if ``fact.status`` is not in ``_VALID_STATUSES``.
        """
        if fact.status not in _VALID_STATUSES:
            raise ValueError(
                f"status must be one of {sorted(_VALID_STATUSES)!r}, "
                f"got {fact.status!r}"
            )
        # Secret redaction (ALWAYS-ON; escape hatch ENGRAM_REDACT_SECRETS=0).
        # P1 (audit 2026-06-07): hippo_remember stored API keys / tokens /
        # private keys VERBATIM -> recalled back into context. redact_secrets was
        # wired only on the transcript path; apply it to EVERY curated fact write.
        # Conservative: high-confidence secret patterns only, never generic PII.
        import os as _os
        if _os.environ.get("ENGRAM_REDACT_SECRETS", "on").strip().lower() not in (
            "0", "off", "false", "no",
        ):
            from .redaction import redact_secrets as _redact_secrets
            _red, _n = _redact_secrets(fact.proposition)
            if _n:
                fact.proposition = _red
        # Unicode sanitize (ALWAYS-ON; escape hatch ENGRAM_UNICODE_SANITIZE=0).
        # F1 C4 (virgin-corpus MuSiQue 2026-07-10, docs/F1_VIRGIN_CORPUS_
        # FINDINGS.md): `unicode_smuggling` fired on the CHARACTERS themselves
        # (U+FEFF in Wikipedia coordinates, U+200B in IPA blocks) and
        # quarantined 4.0% of questions' GOLD paragraphs = silent recall loss
        # on legitimate document text. Strip the invisible code points BEFORE
        # any detector (screen below AND admission gate) — removal never
        # changes what a human reads, it NEUTRALIZES the smuggling channel
        # instead of hiding the fact, and a keyword broken by invisibles
        # ("ig​nore … instructions") becomes MORE detectable. Visible
        # unicode (IPA, accents, homoglyphs) is untouched: content/homoglyph
        # detectors still see it. Non-silent: every strip is logged with the
        # attribution (gate_router — whose claim is this?).
        if _os.environ.get("ENGRAM_UNICODE_SANITIZE", "on").strip().lower() not in (
            "0", "off", "false", "no",
        ):
            from .gate_router import attribution_question as _gr_attr
            from .gate_router import classify_provenance as _gr_classify
            from .prompt_injection import sanitize_dangerous_unicode as _pi_sanitize
            _clean_p, _n_p = _pi_sanitize(fact.proposition)
            _clean_t, _n_t = _pi_sanitize(getattr(fact, "topic", "") or "")
            if _n_p or _n_t:
                if _n_p:
                    fact.proposition = _clean_p
                if _n_t:
                    fact.topic = _clean_t
                _LOG.warning(
                    "unicode sanitize: stripped %d invisible char(s) from "
                    "fact id=%s topic=%s at ingest (smuggling channel "
                    "neutralized; content admitted on its visible text; %s)",
                    _n_p + _n_t, getattr(fact, "id", "?"),
                    getattr(fact, "topic", "?"),
                    _gr_attr(_gr_classify(
                        getattr(fact, "writer_role", None),
                        list(fact.verified_by or []))),
                )
        # Security screen (ALWAYS-ON; escape hatch ENGRAM_INJECTION_SCREEN=0).
        # 2026-06-07: prompt-injection / memory-poisoning defense. A poisoned
        # proposition recalled verbatim into an agent's context can hijack it —
        # the malicious form of the memory-poisoning hole admission_gate cites.
        # Non-lossy: quarantine (rank -1, hidden from default recall) — never
        # dropped, recoverable for audit. mem0 / engram-memory ship no such screen.
        # Runs BEFORE the verified-refs gate so a poisoned 'verified' write is
        # quarantined rather than merely demoted to model_claim (still recallable).
        import os as _os
        if (
            fact.status != "quarantined"
            and _os.environ.get("ENGRAM_INJECTION_SCREEN", "on").strip().lower()
            not in ("0", "off", "false", "no")
        ):
            from .prompt_injection import detect_injection as _detect_injection
            _iv = _detect_injection(fact.proposition)
            # #3 (audit save-path 2026-06-14): anche il TOPIC e' caller-controlled
            # e viene ritornato verbatim dal recall (mcp_server lo echo-a in ogni
            # hit) -> un payload di injection nel topic era un vettore non coperto
            # (solo la proposition era scansionata). Stessa policy non-lossy
            # (quarantena). topic = label corta -> costo trascurabile.
            _iv_topic = _detect_injection(getattr(fact, "topic", "") or "")
            if _iv.is_injection or _iv_topic.is_injection:
                # task #25: the event carries the ownership answer (Aurelio's
                # "backpropagation chiedendo") — attribution never weakens the
                # defense, a content attack quarantines for EVERY provenance.
                from .gate_router import attribution_question as _gr_attr
                from .gate_router import classify_provenance as _gr_classify
                _LOG.warning(
                    "prompt-injection signals prop=%s topic=%s in fact id=%s "
                    "topic=%s -> quarantined (%s)",
                    _iv.signals, _iv_topic.signals,
                    getattr(fact, "id", "?"), getattr(fact, "topic", "?"),
                    _gr_attr(_gr_classify(
                        getattr(fact, "writer_role", None),
                        list(fact.verified_by or []))),
                )
                fact.status = "quarantined"
        # Admission gate (2026-06-04) — OPT-IN via ENGRAM_ADMISSION_GATE, default
        # OFF = byte-identical legacy behavior. When ON, telemetry-topic writes
        # (bus/metric/alloc/lock/tx/nego/replay/dialog-voice) are routed to a
        # SEPARATE `telemetry` table so the curated `facts` corpus stays signal
        # (measured 2026-06-04: only 40.6% of the live store was curated-clean;
        # 55% was telemetry exhaust). Non-lossy. OFF -> this block is skipped.
        from .admission_gate import ROUTE_TELEMETRY, classify_admission, gate_enabled
        if gate_enabled():
            _verdict = classify_admission(
                topic=fact.topic, proposition=fact.proposition,
                status=fact.status,
                writer_role=getattr(fact, "writer_role", "agent_inference"),
                source_episodes=fact.source_episodes,
            )
            if _verdict.decision == ROUTE_TELEMETRY:
                self._store_telemetry(fact)
                # 0.7.0 default-ON migration: AFTER the route succeeded (the
                # message states "was routed" — it must not run ahead of the
                # fact), tell the operator once per process, unless they
                # already chose explicitly via env.
                from .admission_gate import warn_default_on_migration_once
                warn_default_on_migration_once()
                return False if return_replaced else None
            # Honor the rest of the verdict (audit P1 2026-06-07): pre-fix ONLY
            # ROUTE_TELEMETRY was acted on, so REJECT_POLLUTED (leaked tool-call
            # markup) and FLAG_INJECTION fell through and still entered the
            # curated corpus. Non-lossy, mirroring the injection screen above —
            # anything the gate refuses to admit is quarantined (rank -1, hidden
            # from default recall, kept for audit), never dropped. ACCEPT and
            # FLAG_LOW_PROVENANCE carry admit_to_curated=True -> unaffected.
            if not _verdict.admit_to_curated and fact.status != "quarantined":
                from .gate_router import attribution_question as _gr_attr
                from .gate_router import classify_provenance as _gr_classify
                _LOG.warning(
                    "admission gate %s id=%s topic=%s -> quarantined (%s; %s)",
                    _verdict.decision, getattr(fact, "id", "?"),
                    getattr(fact, "topic", "?"), _verdict.reason,
                    _gr_attr(_gr_classify(
                        getattr(fact, "writer_role", None),
                        list(fact.verified_by or []))),
                )
                fact.status = "quarantined"
        # Cycle #111 v2 (2026-05-16) hard-gate with I/O verify (PR #50 v1
        # was security theatre — 12 format-valid but semantically-void
        # refs slipped through). v2 contract:
        #
        #   status='verified'    → at least one verified_by ref must pass
        #                          empirical verification (filesystem for
        #                          file:<path>:<line> or git rev-parse for
        #                          commit <sha>). If repo_root is None,
        #                          NO ref can verify → demote.
        #   status='provisional' → at least one verified_by ref must match
        #                          the URL/arxiv whitelist pattern (no I/O
        #                          check; provisional means "cited but not
        #                          empirically validated").
        #   model_claim / legacy_unverified → no gate.
        #
        # On gate failure: log WARNING + mutate fact.status='model_claim'
        # in-place. The fact still lands on disk (resilient — no caller
        # breakage) but with the correct trust label.
        # Cycle 2026-05-27 round 12 F-fix: trusted-hook bypass also
        # skips the verified_by hard-gate. Retrospective continuity
        # snapshots (writer_role IN TRUSTED + meta_narrative=True) are
        # narrative recaps — their evidence is the SESSION itself, not
        # a filesystem ref the I/O verifier can stat. Without this
        # short-circuit the gate would demote them to model_claim
        # despite the upstream anti_confab_gate having already approved
        # persist at verified.
        # Security fix 2026-06-02 (sorelle loop): token-gate the
        # provenance-skip. writer_role is client-spoofable (set via MCP
        # arguments at mcp_server hippo_remember), so the bypass now also
        # requires the server-side ENGRAM_HOOK_TOKEN via verify_trusted_writer
        # (fail-closed: None/missing token → predicate False → refs gate runs).
        from .trusted_writer import verify_trusted_writer
        _trusted_provenance = (
            bool(getattr(fact, "meta_narrative", False))
            and verify_trusted_writer(
                getattr(fact, "writer_role", "agent_inference"), hook_token,
            )
        )
        if fact.status == "verified" and not _trusted_provenance:
            if not validate_verified_refs(
                list(fact.verified_by or []), repo_root=self.repo_root,
            ):
                _LOG.warning(
                    "verified_by hard-gate (v2): fact_id=%s topic=%s "
                    "demoted to model_claim "
                    "(no verified_by ref passed I/O verification; "
                    "repo_root=%s, refs=%r)",
                    fact.id, fact.topic, self.repo_root,
                    list(fact.verified_by or []),
                )
                fact.status = "model_claim"
        elif fact.status == "provisional":
            if not validate_provisional_refs(list(fact.verified_by or [])):
                _LOG.warning(
                    "provisional gate: fact_id=%s topic=%s demoted to "
                    "model_claim (no verified_by ref matched URL/arxiv "
                    "whitelist, refs=%r)",
                    fact.id, fact.topic, list(fact.verified_by or []),
                )
                fact.status = "model_claim"
        # Cycle #128 (2026-05-17) — L1 anti-confabulation: emit a
        # warning when the proposition contains a SHIPPED-like keyword
        # but verified_by lacks commit-tracking refs. The fact is STILL
        # saved (back-compat) — only a warning is logged for later L2
        # reconciler scrubbing. Empirical motivation: 2/7 confabulations
        # in session 2026-05-17 (cycle 119/120 SHIPPED claim pre-merge).
        # task #25 (F1 C2): L1.x grade the AGENT's own status claims — a
        # document paragraph saying "the companies merged" or "the case is
        # open" is NOT the agent claiming a merge/state. Route by provenance
        # (gate_router): external_content / user_input skip the L1.x
        # heuristics; agent claims and hooks keep the full discipline.
        # Warning-only detectors, so this routing is a semantic fix with
        # ZERO security surface (injection/refs gates above already ran).
        from .anti_confabulation import (
            detect_unsupported_diagnosis_claim,
            detect_unsupported_shipped_claim,
            detect_unsupported_task_state_claim,
        )
        from .gate_router import classify_provenance as _gr_classify
        from .gate_router import l1x_applies as _gr_l1x_applies
        if _gr_l1x_applies(_gr_classify(
                getattr(fact, "writer_role", None),
                list(fact.verified_by or []))):
            _l1_warning = detect_unsupported_shipped_claim(
                proposition=fact.proposition,
                verified_by=list(fact.verified_by or []),
            )
            if _l1_warning:
                _LOG.warning(
                    "L1 anti-confabulation: fact_id=%s topic=%s — %s",
                    fact.id, fact.topic, _l1_warning,
                )
            # Cycle #130 (2026-05-17): L1.5 diagnosis detector.
            # Same no-breaking contract — fact is stored anyway.
            _l15_warning = detect_unsupported_diagnosis_claim(
                proposition=fact.proposition,
                verified_by=list(fact.verified_by or []),
            )
            if _l15_warning:
                _LOG.warning(
                    "L1.5 anti-confabulation: fact_id=%s topic=%s — %s",
                    fact.id, fact.topic, _l15_warning,
                )
            # Cycle #131 (2026-05-17): L1.7 task-state detector.
            # Same no-breaking contract — fact is stored anyway.
            _l17_warning = detect_unsupported_task_state_claim(
                proposition=fact.proposition,
                verified_by=list(fact.verified_by or []),
            )
            if _l17_warning:
                _LOG.warning(
                    "L1.7 anti-confabulation: fact_id=%s topic=%s — %s",
                    fact.id, fact.topic, _l17_warning,
                )
        # S2 (F1 adversarial scenario map, 2026-07-10): non-silent over-window
        # guard. e5 truncates at ~512 tokens; a long fact — a whole document
        # pasted into add() — embeds only its HEAD and drops the rest SILENTLY
        # (QuALITY: 115/115 articles > 512 tok, direct store sees ~7%). Warn,
        # NEVER truncate the stored text, and point at the document tier
        # (DocumentIndex chunks + cites). Heuristic char threshold: CJK packs
        # more tokens per char, so this warns EARLY rather than late. Env
        # ENGRAM_LONG_FACT_WARN_CHARS (default 2000 ≈ conservative 512-tok
        # head); 0 disables. Applies to EVERY provenance (a long agent claim is
        # just as truncated as a long document).
        try:
            _long_warn = int(os.environ.get("ENGRAM_LONG_FACT_WARN_CHARS", "2000"))
        except ValueError:
            _long_warn = 2000
        if _long_warn and len(fact.proposition or "") > _long_warn:
            from .gate_router import attribution_question as _gr_attr2
            from .gate_router import classify_provenance as _gr_classify2
            _LOG.warning(
                "long fact: id=%s topic=%s is %d chars — beyond the embedder "
                "window (~512 tokens); recall will only see the head. For whole "
                "documents use DocumentIndex/index_file (chunked + cited). %s",
                fact.id, fact.topic, len(fact.proposition),
                _gr_attr2(_gr_classify2(
                    getattr(fact, "writer_role", None),
                    list(fact.verified_by or []))),
            )
        # 2026-06-05: decouple persistence from embedding so a save NEVER
        # blocks ~22s on a cold model load (root cause of the "Engram hangs
        # on save" incident — measured: cold encode 21.8s, daemon-warm 40ms).
        #   embed="sync"  (default) = embed now; byte-identical legacy path.
        #   embed="defer"           = store empty-blob sentinel now; backfill
        #                             (save is instant; row invisible to
        #                             cosine recall until backfilled, but
        #                             still keyword-findable).
        #   embed="auto"            = embed now IFF the encode daemon is warm,
        #                             else defer (never cold-load on the hot
        #                             path).
        _embed_mode = embed
        _via_auto = (embed == "auto")
        if _embed_mode == "auto":
            try:
                from . import encode_service as _es
                if _es.daemon_usable():
                    _embed_mode = "sync"
                else:
                    # Daemon cold/down → defer (instant save) AND kick it awake
                    # (non-blocking spawn) so the backfill + the NEXT save are
                    # fast. Self-healing: the system recovers warmth on its own.
                    _embed_mode = "defer"
                    try:
                        _es.ensure_running()
                    except Exception:  # noqa: BLE001
                        pass
            except Exception:  # noqa: BLE001 — fail toward DEFER, never cold-load
                # Hang-safety (2026-06-06): if the daemon-warmth check itself
                # errors, DEFER rather than fall to a sync cold-load. A dead /
                # hung daemon + a slow in-process load is exactly the 40-min
                # save-hang to avoid — memory must never block the caller.
                _embed_mode = "defer"
        if _embed_mode == "defer":
            emb = None
        elif _via_auto:
            # auto resolved to "sync" (daemon looked warm) — still BOUND it: an
            # alive-but-starved daemon can answer the warmth ping yet be slow to
            # encode. On budget-overrun → defer, never hang the write.
            emb = _encode_within_budget(fact.proposition)
        else:
            # explicit embed="sync" — byte-identical legacy path (tests rely on it)
            emb = embedding.encode(embedding.as_passage(fact.proposition))
        verified_by_json = json.dumps(list(fact.verified_by or []))
        with self._connect() as conn:
            was_existing = False
            if return_replaced:
                row = conn.execute(
                    "SELECT 1 FROM facts WHERE id = ? LIMIT 1",
                    (fact.id,),
                ).fetchone()
                was_existing = row is not None
            # Cycle 160 (2026-05-19) pattern card v5 columns. Serialised
            # the same way ``source_episodes`` is — comma-separated TEXT,
            # ``None`` when empty/missing so legacy callers store NULL
            # rather than empty strings. The ``_row`` reader mirrors this.
            tk = ",".join(fact.trigger_keywords) if fact.trigger_keywords else None
            lt = ",".join(fact.lineage_to) if fact.lineage_to else None
            df = ",".join(getattr(fact, "derives_from", []) or []) or None
            # SCAN-68 FIX 2026-06-02 (NONNA): era INSERT OR REPLACE, che su
            # re-store dello stesso id AZZERAVA superseded_by/at/reason (colonne
            # non listate, DELETE+INSERT) -> fatti soppressi resuscitavano. Ora
            # UPSERT esplicito: aggiorna SOLO le colonne di contenuto, PRESERVA
            # la supersession esistente (non in INSERT-list ne in DO UPDATE).
            #
            # NOTA (regressione del fix NONNA sopra): il partial UNIQUE INDEX
            # `idx_facts_auto_master_unique` (cycle 157) su facts(topic) WHERE
            # superseded_by IS NULL AND proposition LIKE 'AUTO-CLUSTER-MASTER%'
            # NON e' gestito qui di proposito. Un secondo master live con stesso
            # topic (id diverso) solleva sqlite3.IntegrityError = fail-fast:
            # e' il chiamante che crea master (consolidation._persist_master) a
            # catturarlo come race-losing graceful. NON aggiungere una 2nd
            # clausola ON CONFLICT(topic): renderebbe store() dipendente
            # dall'esistenza dell'indice e romperebbe OGNI insert su un DB dove
            # l'indice non c'e' ancora (es. pre-migration v4).
            # v8 (2026-06-03) buco #3: il fatto e' "verificato quando creato"
            # se il chiamante non specifica un last_verified_at esplicito.
            lv_at = (
                fact.last_verified_at
                if getattr(fact, "last_verified_at", None) is not None
                else fact.created_at
            )
            # ANTI-SPOOF v8.1 (buco #3b): osservabilita' del tentativo di
            # falsificare la freschezza con un timestamp nel futuro. NON
            # alteriamo/clampiamo il valore (il fail-closed in recall lo
            # esclude e l'audit deve poter VEDERE il dato manomesso); qui
            # solo un WARNING, come il demote-log del buco #1 writer_role.
            if lv_at is not None and lv_at > time.time():
                _LOG.warning(
                    "anti-spoof freshness: fact_id=%s topic=%s ha "
                    "last_verified_at nel futuro (%.0f > now) — sara' "
                    "trattato come stantio (fail-closed) dal recall",
                    fact.id, fact.topic, lv_at,
                )
            conn.execute(
                """INSERT INTO facts
                (id, proposition, topic, confidence, source_episodes,
                 created_at, embedding, verified_by, status, source_signature,
                 trigger_keywords, applicable_when, worked_example, lineage_to,
                 writer_role, meta_narrative, last_verified_at, embedding_model,
                 valid_until, derives_from, grounding_score, asserted_at,
                 epistemic, confidence_tier)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                 proposition=excluded.proposition, topic=excluded.topic,
                 confidence=excluded.confidence,
                 source_episodes=excluded.source_episodes,
                 created_at=excluded.created_at,
                 -- P0-3 (audit 2026-06-07): a deferred re-store binds emb=b''.
                 -- PRESERVE the existing vector when the incoming one is empty,
                 -- else a re-save under a cold daemon drops the fact from recall.
                 embedding=CASE WHEN length(excluded.embedding) > 0
                     THEN excluded.embedding ELSE facts.embedding END,
                 verified_by=excluded.verified_by, status=excluded.status,
                 source_signature=excluded.source_signature,
                 trigger_keywords=excluded.trigger_keywords,
                 applicable_when=excluded.applicable_when,
                 worked_example=excluded.worked_example,
                 lineage_to=excluded.lineage_to,
                 writer_role=excluded.writer_role,
                 meta_narrative=excluded.meta_narrative,
                 -- #4 (audit save-path 2026-06-14): UPSERT MONOTONO su
                 -- last_verified_at. Un deferred-replay che riapplica uno
                 -- snapshot stale (crash tra il commit e il done-marker) NON
                 -- deve regredire un last_verified_at piu' fresco alzato nel
                 -- frattempo da bump_on_recall (gia' monotono col suo WHERE
                 -- last_verified_at < ?) o da un re-store. CASE esplicito per
                 -- i NULL legacy (no reliance su MAX(NULL) di SQLite). Coerente
                 -- con l'anti-spoof: un futuro resta (il recall lo fail-closa).
                 last_verified_at=CASE
                     WHEN excluded.last_verified_at IS NULL
                         THEN facts.last_verified_at
                     WHEN facts.last_verified_at IS NULL
                         THEN excluded.last_verified_at
                     WHEN facts.last_verified_at > excluded.last_verified_at
                         THEN facts.last_verified_at
                     ELSE excluded.last_verified_at END,
                 embedding_model=CASE WHEN length(excluded.embedding) > 0
                     THEN excluded.embedding_model ELSE facts.embedding_model END,
                 valid_until=excluded.valid_until,
                 derives_from=excluded.derives_from,
                 -- v12: preserve a known grounding score if the re-store doesn't carry one
                 -- (None), else take the new one — mirrors the embedding-preserve guard.
                 grounding_score=CASE WHEN excluded.grounding_score IS NOT NULL
                     THEN excluded.grounding_score ELSE facts.grounding_score END,
                 -- v13: preserve a known event time on re-store without one.
                 asserted_at=CASE WHEN excluded.asserted_at IS NOT NULL
                     THEN excluded.asserted_at ELSE facts.asserted_at END,
                 -- v14: a re-store without a label must NOT clobber one earned
                 -- via set_epistemic (whose monotone rules a plain store()
                 -- bypasses); an explicit incoming label wins.
                 epistemic=CASE WHEN excluded.epistemic IS NOT NULL
                     THEN excluded.epistemic ELSE facts.epistemic END,
                 confidence_tier=excluded.confidence_tier""",
                (
                    fact.id, fact.proposition, fact.topic, fact.confidence,
                    ",".join(fact.source_episodes), fact.created_at,
                    embedding.serialize(emb) if emb is not None else b"",
                    verified_by_json, fact.status, fact.source_signature,
                    tk, fact.applicable_when, fact.worked_example, lt,
                    getattr(fact, "writer_role", "agent_inference"),
                    1 if getattr(fact, "meta_narrative", False) else 0,
                    lv_at,
                    embedding.model_signature() if emb is not None else "",
                    getattr(fact, "valid_until", None),
                    df,
                    getattr(fact, "grounding_score", None),
                    getattr(fact, "asserted_at", None),
                    (_epistemic.serialize(fact.epistemic)
                     if getattr(fact, "epistemic", None) else None),
                    getattr(fact, "confidence_tier", None),
                ),
            )
        # Entity-live write path (2026-06-10, critic caveat on 2aa6769):
        # the one-shot backfill populated the KG but new facts never entered
        # it. Ingest extract→link→co-occur edges HERE, after the row commits.
        # Best-effort by contract: the entity KG is a separate sibling DB
        # (entity_kg_path_for — tests stay hermetic, never the global
        # CONFIG.data_dir), and any failure is swallowed with a warning —
        # a KG hiccup must never break a memory write. Quarantined/orphaned
        # facts are excluded, mirroring populate_entity_graph's batch policy.
        if fact.status not in ("quarantined", "orphaned") and _entity_live_enabled():
            try:
                # Lazy-skip BEFORE touching the KG: extraction is a pure ~1 ms
                # regex pass, while EntityStore init (mkdir + migrations) is
                # the cost that broke the 3 s anti-hang guard on the cold
                # windows CI runner (4.2 s measured). Zero entities → the KG
                # db is never even created.
                from .entity_extract_lite import extract_entities_lite
                _ents = extract_entities_lite(fact.proposition or "")
                if _ents:
                    from .entity_populate import (
                        entity_kg_path_for,
                        populate_entities_for_fact,
                    )
                    kg = getattr(self, "_entity_kg", None)
                    if kg is None or getattr(kg, "db_path", None) != entity_kg_path_for(self.db_path):
                        from .entity_kg import EntityStore
                        kg = EntityStore(db_path=entity_kg_path_for(self.db_path))
                        self._entity_kg = kg
                    populate_entities_for_fact(
                        fact.id, fact.proposition, kg, entities=_ents,
                    )
            except Exception as exc:  # noqa: BLE001 — KG must never break store
                _LOG.warning("entity-live populate failed (ignored): %s", exc)
        # P1 truth-reconciliation on write (opt-in, default OFF). After the fact
        # is entity-linked, find shared-entity update candidates and reconcile
        # (fail-safe: contest, never auto-supersede). Best-effort — a reconcile
        # hiccup must never break a memory write.
        if _reconcile_on_write_enabled() and fact.status not in (
            "quarantined", "orphaned",
        ):
            try:
                # Use the semantic NLI judge if the application wired one
                # (set_reconcile_judge) — validated to ~4× conflict-recall over the
                # lexical default at no precision cost (benchmark/reconcile_truth_
                # maintenance.py --nli). None -> lexical heuristic (unchanged default).
                _auto = _reconcile_auto_supersede_enabled()
                _strict, _tiered = _reconcile_evidence_policy(_auto)
                self.reconcile_new_fact(
                    fact, judge=getattr(self, "_reconcile_judge", None),
                    auto_supersede=_auto,
                    require_evidence=_strict, protect_evidenced=_tiered)
                # NOTE (task #20b REVERTED, mini-world regression 2026-07-10):
                # feeding supersessions into the source-trust OUTCOME channel
                # is an attribution error (law L3). Under churn an honest
                # source's fact is superseded by newer truth CONSTANTLY — that
                # is the world moving, NOT the source lying. The hook made
                # honest sources accumulate blame, sink, and get retro-demoted
                # (mini-world stale 0.10 -> 1.00). Supersession must feed NO
                # source penalty; the outcome channel needs an
                # independent-verification signal, not a temporal one.
            except Exception as exc:  # noqa: BLE001 — reconcile must never break store
                _LOG.warning("reconcile-on-write failed (ignored): %s", exc)
        # Auto-confirmation on write (opt-in, default OFF). Same-topic agreement
        # from distinct cited sources feeds the source-trust consistency channel
        # with independence-aware acceptance. Best-effort — never breaks a write.
        if _source_auto_confirm_enabled() and fact.status not in (
            "quarantined", "orphaned",
        ):
            try:
                self._auto_confirm_source_trust(fact)
            except Exception as exc:  # noqa: BLE001 — must never break store
                _LOG.warning("auto-confirm source-trust failed (ignored): %s", exc)
        # Cycle #116 (2026-05-17): optional post-store coherence hook.
        # When provided, runs after the row is committed so the caller
        # can inspect the just-stored fact against its topic siblings.
        # Conservative by design: hook exceptions are SWALLOWED (with a
        # logged warning) so a buggy hook can never break store(). The
        # hook is observational — it cannot mutate the stored row.
        if coherence_hook is not None:
            try:
                coherence_hook(fact, self)
            except Exception as exc:  # noqa: BLE001 — hook must never break store
                _LOG.warning(
                    "coherence_hook failed: fact_id=%s topic=%s error=%s",
                    fact.id, fact.topic, exc,
                )
        # Cycle #135: invalidate the recall cache on store/replace.
        # The bump is cheap (atomic int +1); the cache rebuilds lazily
        # on the next recall(topic=None) call.
        self._cache_version += 1
        return was_existing if return_replaced else None

    def backfill_pending_embeddings(self, *, limit: int | None = None) -> int:
        """Embed rows persisted with ``embed='defer'`` (NULL embedding) and
        make them recallable. Returns the number embedded.

        The async other half of non-blocking store(): a save persists the row
        instantly with an empty-blob (length-0) sentinel — no ~22s cold-load
        risk; this fills the vector in afterwards — callable by the encode
        daemon, a periodic task, or the engram CLI. An empty-blob row is
        already excluded from BOTH semantic-recall paths by the existing
        ``length(embedding) = ?`` shape
        filter, so it is invisible to cosine until backfilled (still keyword-
        findable meanwhile). Idempotent: returns 0 when nothing is pending.
        Per-row encode errors are logged and skipped, never aborting the run.

        A-8 (audit#2 2026-06-08): the UPDATE is gated on ``proposition = ?``
        (the exact text that was encoded), not just ``length(embedding) = 0``.
        If a concurrent writer edits the proposition between this SELECT and the
        UPDATE, the row no longer matches and is left for the next pass — the
        stale vector of the OLD text is never written onto the NEW text (which
        would be a cosine-space poisoning). The return count reflects rows that
        ACTUALLY updated (rowcount), so a skipped race is not over-counted.
        """
        # Structural-safety hardening (2026-06-13): a row is STALE — invisible
        # to semantic recall — when it fails EITHER half of the recall's own
        # active-row filter (length == expected_bytes AND
        # COALESCE(embedding_model, legacy) == active). That covers three real
        # corpus states found live: empty blob (length 0), a wrong-dim legacy
        # blob (e.g. 384-d MiniLM), and a correct-dim blob with NULL/wrong
        # embedding_model. Previously only length==0 healed, so a fact saved by
        # ANY path that wrote the wrong model stayed silently unrecallable. We
        # re-encode from the proposition with the ACTIVE model, healing all
        # three. Idempotent: once a row is active it no longer matches.
        _active_model = embedding.model_signature()
        _active_bytes = embedding.expected_embedding_bytes()
        _stale_where = (
            "WHERE length(embedding) != ? "
            "OR COALESCE(embedding_model, ?) != ?"
        )
        _stale_params = (_active_bytes, _LEGACY_EMBEDDING_MODEL, _active_model)
        with self._connect() as conn:
            if limit is not None:
                rows = conn.execute(
                    "SELECT id, proposition FROM facts " + _stale_where
                    + " LIMIT ?",
                    (*_stale_params, int(limit)),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT id, proposition FROM facts " + _stale_where,
                    _stale_params,
                ).fetchall()
        n = 0
        for r in rows:
            prop = r["proposition"]
            if not (prop or "").strip():
                continue  # can't encode an empty proposition — leave it
            try:
                emb = embedding.encode(embedding.as_passage(prop))
            except Exception as exc:  # noqa: BLE001 — one bad row never aborts
                _LOG.warning(
                    "backfill_embedding_failed id=%s error=%s", r["id"], exc,
                )
                continue
            with self._connect() as conn:
                # A-8 anti-poisoning gate stays on the proposition (the exact
                # text encoded); the length==0 gate is GONE so non-empty stale
                # blobs are actually overwritten. Idempotent because the SELECT
                # above no longer matches an active row.
                cur = conn.execute(
                    "UPDATE facts SET embedding = ?, embedding_model = ? "
                    "WHERE id = ? AND proposition = ?",
                    (embedding.serialize(emb), _active_model,
                     r["id"], prop),
                )
                updated = cur.rowcount
            if updated:  # 0 if the proposition changed under us — leave for next pass
                n += 1
        if n:
            self._cache_version += 1  # invalidate the recall hot-path cache
        return n

    def all(self) -> list[Fact]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM facts ORDER BY created_at DESC").fetchall()
        return [self._row(r) for r in rows]

    def live_topic_siblings(self, topic: str, *, limit: int = 200) -> list[Fact]:
        """LIVE same-topic facts a NEW write should be checked against for
        contradiction (the opt-in write-path NLI moat): non-superseded, and not
        quarantined / orphaned / user_belief (those are out of trusted recall).

        Excluding already-retired facts is CORRECTNESS, not just cost — flagging a
        contradiction against a value that was already superseded or quarantined is a
        false positive. Indexed on ``topic`` (idx_facts_topic) + bounded by ``limit``,
        so the moat does not materialize the whole store the way ``all()`` does.
        Most-recent first. Empty topic → ``[]``.
        """
        t = (topic or "").strip()
        if not t:
            return []
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM facts WHERE topic = ? AND superseded_by IS NULL "
                "AND status NOT IN ('orphaned', 'quarantined', 'user_belief') "
                "ORDER BY created_at DESC LIMIT ?", (t, int(limit))).fetchall()
        return [self._row(r) for r in rows]

    def get(self, fact_id: str, *, live_only: bool = False) -> Fact | None:
        """Fetch one Fact by id. Returns None if not found.

        Added cycle #52 (2026-05-14) for symmetry with EpisodicMemory.get
        and SkillLibrary.get — needed by `hippo_lineage_trace` walker
        to resolve fact-kind node labels without scanning all().

        live_only (correctness-hunt #3, HIGH-2, 2026-06-13): when True, a
        superseded / orphaned / quarantined fact resolves to None. The
        unfiltered default is needed by lineage/supersede-chain walkers, but
        recall-style consumers (anchor/PPR rendering into the self-model,
        fusion extras) MUST pass live_only=True so a retracted fact is never
        surfaced as current. Giro 2: ``user_belief`` joins the hidden set —
        every live_only consumer surfaces facts AS CURRENT TRUTH, which is
        precisely what an unverified user assertion must not be; without this,
        the default-ON PPR/BM25 fusion resurrected beliefs into the default
        view through its extra-id fetch (found by the sweep, pinned by
        ``test_fusion_extras_cannot_resurrect_beliefs_into_default_view``).
        """
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM facts WHERE id = ? LIMIT 1", (fact_id,),
            ).fetchone()
        if not row:
            return None
        f = self._row(row)
        if live_only and (
            getattr(f, "superseded_by", None)
            or getattr(f, "status", "") in (
                "orphaned", "quarantined", "user_belief")
        ):
            return None
        return f

    def set_epistemic(self, fact_id: str, label: dict) -> bool:
        """Apply an epistemic label under the MONOTONE transition rules
        (v14, engram/epistemic.py): first labeling free; an ``unbeaten`` bound
        only grows; ``refuted`` is absorbing; ``proven`` never silently
        downgrades. Returns False (nothing written) on an unknown id or a
        forbidden transition — the stored label is the invariant, not the
        caller's wish. Guarded UPDATE: the WHERE re-checks the current value so
        a concurrent writer cannot slip a forbidden transition between our read
        and our write (same discipline as the monotone last_verified_at)."""
        current = self.get(fact_id)
        if current is None or not _epistemic.can_transition(
                current.epistemic, label):
            return False
        prev_raw = (_epistemic.serialize(current.epistemic)
                    if current.epistemic else None)
        with self._connect() as conn:
            cur = conn.execute(
                "UPDATE facts SET epistemic = ? WHERE id = ? "
                "AND (epistemic IS ? OR epistemic = ?)",
                (_epistemic.serialize(label), fact_id, prev_raw,
                 prev_raw or ""),
            )
            conn.commit()
            changed = cur.rowcount > 0
        if changed:
            self._cache_version += 1  # recall hot-path cache must see the label
        return changed

    def set_derives_from(self, fact_id: str, parent_ids: list[str]) -> bool:
        """Declare the LOGICAL derivation edge (v11 ``derives_from``) of an
        existing fact — used by the composer AFTER the gate admits a derived
        candidate (the add() path has no derives_from parameter; admission and
        tracing are two steps by design: the gate never trusts the trace).
        Returns False on an unknown id."""
        clean = ",".join(p for p in parent_ids if p)
        with self._connect() as conn:
            cur = conn.execute(
                "UPDATE facts SET derives_from = ? WHERE id = ?",
                (clean, fact_id))
            conn.commit()
            changed = cur.rowcount > 0
        if changed:
            self._cache_version += 1
        return changed

    def filter_live_ids(self, fact_ids: list[str]) -> list[str]:
        """Return the subset of ``fact_ids`` that are LIVE (superseded_by IS
        NULL and status not orphaned/quarantined), preserving input order.

        Correctness-hunt #3 (HIGH-2): entity_facts links are created under a
        live filter but never removed on supersede/orphan, so PPR/anchor/
        entity recall returns dead ids. Consumers run their id list through
        this before rendering/returning so retracted facts don't leak."""
        if not fact_ids:
            return []
        ph = ",".join("?" for _ in fact_ids)
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT id FROM facts WHERE id IN ({ph}) "  # noqa: S608 - ph is '?,?'
                "AND superseded_by IS NULL "
                "AND status NOT IN ('orphaned', 'quarantined', 'user_belief')",
                fact_ids,
            ).fetchall()
        live = {r["id"] for r in rows}
        return [fid for fid in fact_ids if fid in live]

    def list_facts(self, *, limit: int = 10000, offset: int = 0,
                    topic: str | None = None,
                    include_superseded: bool = False,
                    hide_low_trust: bool = False) -> list[Fact]:
        """CYCLE #10 fix: paginated list. mcp_server.py called
        a.semantic.list_facts(limit=..., offset=0) in 28 places, but the
        method did not exist → AttributeError → caught by bare
        `except Exception: pass` → 28 MCP tools silently returned facts=[].

        This adapter preserves the existing call-shape and lets all the
        affected tools (hippo_facts_find_duplicates, hippo_facts_topics,
        hippo_facts_disagreement, hippo_facts_aggregate_overall,
        hippo_facts_cluster_by_topic, hippo_facts_export_all, ...)
        actually see the real corpus.

        Args:
            limit: max rows returned (cap, also enforced by SQL LIMIT).
            offset: pagination offset.
            topic: if set, restrict to that topic.

        Returns:
            list[Fact] sorted by created_at DESC.
        """
        with self._connect() as conn:
            clauses: list[str] = []
            params: list[Any] = []
            if topic:
                clauses.append("topic = ?")
                params.append(topic)
            if not include_superseded:
                clauses.append("superseded_by IS NULL")
            if hide_low_trust:
                # The statuses recall hides (_STATUS_RANK < 0). Opt-in, so the
                # 28 analysis/cleanup callers still see the whole corpus; the
                # proactive briefing sets it so it never presents a
                # gate-rejected claim as a "recent fact" (2026-07-20).
                clauses.append(
                    "COALESCE(status,'model_claim') "
                    "NOT IN ('orphaned','quarantined','user_belief')")
            sql = "SELECT * FROM facts"
            if clauses:
                sql += " WHERE " + " AND ".join(clauses)
            sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([int(limit), int(offset)])
            rows = conn.execute(sql, tuple(params)).fetchall()
        return [self._row(r) for r in rows]

    def _get_corpus_cache(
        self,
    ) -> tuple[list[Fact], np.ndarray, np.ndarray, np.ndarray]:
        """Cycle #135: lazy build of the recall hot-path cache.

        Returns the current corpus as ``(facts, matrix, lv)`` where
        ``facts[i]``, ``matrix[i]`` and ``lv[i]`` index the SAME row.
        Rebuilds from disk only when ``self._cache_version`` has been bumped
        by a store/delete. Restricted to the default-filter view:
        live rows (``superseded_by IS NULL``) only.

        Thread-safety (sorelle loop 2026-06-03): validate + build + swap run
        under ``self._cache_lock``. The returned triple is read from ONE
        consistent snapshot (the validated cache dict, or the freshly built
        one) so facts/matrix/lv can never come from different dicts (torn
        read fixed). The caller must NOT re-read ``self._corpus_cache`` — the
        triple it receives is the atomic view.
        """
        with self._cache_lock:
            # Cache validity = in-memory counter (same-instance mutations,
            # cheap, no I/O) AND SQLite data_version (cross-process/other-
            # connection commits the counter cannot see). Snapshot the cache
            # into a LOCAL so validate and return reference the SAME dict.
            cache = self._corpus_cache
            if (
                cache is not None
                and cache.get("version") == self._cache_version
                and cache.get("data_version") == self._db_data_version()
            ):
                return cache["facts"], cache["matrix"], cache["lv"], cache["vu"]
            # Review 5-lenti C5: a rebuild driven by a CROSS-PROCESS commit
            # (data_version moved, our counter did not) yields a DIFFERENT
            # corpus under the SAME _cache_version — version-keyed consumers
            # (the ANN pool) would keep serving indices computed for the OLD
            # matrix (IndexError on the shrunken facts list / wrong rows).
            # Open a new generation so every such consumer rebuilds.
            if cache is not None and cache.get("version") == self._cache_version:
                self._cache_version += 1
            # Read the cross-process version BEFORE snapshotting rows, so the
            # stored value reflects a state <= the rows about to be read. If a
            # write lands after this point, dv is bumped on the NEXT gate check
            # → rebuild. The reverse (dv ahead of rows) can never make a stale
            # snapshot look fresh.
            dv = self._db_data_version()
            with self._connect() as conn:
                # Cycle #135 cache pre-filters to the default-view rows only.
                # Cycle #137 extends the filter to exclude orphaned rows so
                # the L2-reconciler-scrubbed facts disappear from recall by
                # default. include_orphaned=True at the recall() level falls
                # back to the legacy SQL path which can opt them back in.
                #
                # Cycle 171 (2026-05-22) defensive shape filter — SQL-side,
                # not Python-side, so we never pay a per-row deserialize
                # cost (which regressed cycle 135 sub-linear scaling in the
                # 2026-05-21 mem-architect patch). 384 dim × 4 bytes
                # float32 = 1536. Rows whose embedding blob has any other
                # length (e.g. clp save bug ``embedding=b""`` cycle 171
                # incident, or hypothetical mid-migration dim change) are
                # dropped before they reach np.stack.
                rows = conn.execute(
                    # SCAN-68 (audit): denylist telemetria condivisa con il
                    # legacy path via _TELEMETRY_DENYLIST_SQL (coerenza).
                    "SELECT * FROM facts "
                    "WHERE superseded_by IS NULL "
                    # Giro 2 (2026-07-15): 'user_belief' joins the hidden set — an
                    # unverified USER assertion of fact is out of default recall
                    # (anti-sycophancy), retrievable only on an explicit opt-in.
                    "AND status NOT IN ('orphaned', 'quarantined', 'user_belief') "
                    # Anti-laundering (2026-06-03): le promozioni conversational a
                    # basso-trust (writer_role='conversational_promotion' non ancora
                    # 'verified') NON entrano nella vista di default. Una promozione
                    # poi corroborata con evidenza (status='verified') torna in vista.
                    "AND NOT (writer_role = 'conversational_promotion' "
                    "AND status != 'verified')"
                    + _TELEMETRY_DENYLIST_SQL
                    + "AND length(embedding) = ? "
                    # v9 (Sorella C): isola lo spazio di embedding al modello
                    # attivo. COALESCE -> riga legacy (NULL) trattata come
                    # _LEGACY_EMBEDDING_MODEL. Blocca il poisoning same-dim.
                    "AND COALESCE(embedding_model, ?) = ? "
                    "ORDER BY created_at DESC",
                    (embedding.expected_embedding_bytes(),
                     _LEGACY_EMBEDDING_MODEL, embedding.model_signature()),
                ).fetchall()
            if not rows:
                # Empty corpus: shape only matters for downstream consumers
                # but the cache_eligible branch short-circuits on len==0, so
                # any 2-D empty array is fine.
                empty_matrix = np.zeros((0, 0), dtype=np.float32)
                empty_lv = np.zeros((0,), dtype=np.float64)
                empty_vu = np.zeros((0,), dtype=np.float64)
                self._corpus_cache = {
                    "facts": [],
                    "matrix": empty_matrix,
                    "lv": empty_lv,
                    "vu": empty_vu,
                    "version": self._cache_version,
                    "data_version": dv,
                }
                return [], empty_matrix, empty_lv, empty_vu
            facts = [self._row(r) for r in rows]
            matrix = np.stack(
                [embedding.deserialize(r["embedding"]) for r in rows]
            )
            # v8 (2026-06-03) buco #3: precomputa l'array dei last_verified_at
            # (coalesce None->created_at) AL BUILD della cache, non per-recall.
            # Cosi' il cutoff freshness nel recall e' una maschera numpy
            # vettoriale O(N) in C, NON un loop Python per-fatto (che
            # regredirebbe lo scaling sub-lineare cycle 135 — verificato dal
            # bench test_semantic_recall_perf).
            lv = np.array(
                [
                    f.last_verified_at if f.last_verified_at is not None
                    else f.created_at
                    for f in facts
                ],
                dtype=np.float64,
            )
            # v10 (2026-06-14) valid-time bi-temporale: precomputa l'array dei
            # valid_until AL BUILD (come lv), cosi' l'hard-expire nel recall e'
            # una maschera numpy vettoriale (vu > now) e NON un loop Python
            # per-fatto — preserva lo scaling sub-lineare cycle 135 (bench
            # test_semantic_recall_perf). None -> np.inf == "nessuna scadenza"
            # (vu > now sempre vero -> mai escluso dal cutoff).
            vu = np.array(
                [
                    f.valid_until if f.valid_until is not None else np.inf
                    for f in facts
                ],
                dtype=np.float64,
            )
            self._corpus_cache = {
                "facts": facts,
                "matrix": matrix,
                "lv": lv,
                "vu": vu,
                "version": self._cache_version,
                "data_version": dv,
            }
            return facts, matrix, lv, vu

    def _attach_trust_signals(
        self, hits_2t: list[tuple[Fact, float]],
    ) -> list[tuple]:
        """Cycle #117: post-hoc trust-signal attachment (reused from
        the legacy path so the cache branch shares one impl)."""
        from .contradiction import ContradictionStore
        from .trust_signal import compute_trust_signal
        store = ContradictionStore(self.db_path)
        return [
            (f, sim, compute_trust_signal(
                f, self, contradiction_store=store,
            ))
            for f, sim in hits_2t
        ]

    def _bump_verified(self, hits: list[tuple], now: float) -> None:
        """Bump-on-recall (2026-06-09): refresh ``last_verified_at`` -> ``now``
        for the facts a recall just RETURNED, so actively-used memories don't
        age out under the freshness window (age measured from LAST USE, not
        creation).

        SERVER clock only -> never in the future -> the anti-spoof invariant
        (``_fact_is_stale`` rejects future timestamps) is untouched; and stale
        rows were already filtered out before ``hits`` was built, so a
        future-``last_verified_at`` spoof is never resurrected. Only rows past
        the half-window refresh threshold are written (the common fresh case is
        a no-op -> no write, no cache invalidation). The corpus cache is
        invalidated only when rows actually change. Best-effort: a bump failure
        must never break recall. Opt-out: ``ENGRAM_BUMP_ON_RECALL=0``.
        """
        if not hits or os.environ.get("ENGRAM_BUMP_ON_RECALL", "1") == "0":
            return
        ids = [fid for fid in (getattr(h[0], "id", None) for h in hits) if fid]
        if not ids:
            return
        _ph = ",".join("?" * len(ids))
        try:
            with self._connect() as conn:
                # F3 (2026-06-13): drop the inherited 60s busy_timeout to a
                # short bound for THIS best-effort write. Under a held write
                # lock the UPDATE would otherwise stall recall up to 60s; with
                # a short timeout it raises "database is locked" fast and the
                # except below swallows it — the bump is skipped, recall stays
                # responsive. (DML takes the write lock even when 0 rows match.)
                conn.execute(f"PRAGMA busy_timeout={_bump_busy_timeout_ms()}")
                cur = conn.execute(
                    "UPDATE facts SET last_verified_at = ? "
                    f"WHERE id IN ({_ph}) "
                    "AND (last_verified_at IS NULL OR last_verified_at < ?)",
                    (now, *ids, now - _BUMP_REFRESH_THRESHOLD_S),
                )
                changed = cur.rowcount or 0
            if changed > 0:
                # cached last_verified_at array is now stale -> force rebuild.
                self._cache_version += 1
        except Exception as exc:  # noqa: BLE001 — recall robustness > bump
            _LOG.warning("bump_on_recall_failed: %s", exc)

    def recall(
        self, query: str, k: int = 5, topic: str | None = None,
        *,
        include_superseded: bool = False,
        exclude_legacy: bool = False,
        min_status: str | None = None,
        trust_signals: bool = False,
        include_orphaned: bool = False,
        include_conversational: bool = False,
        include_beliefs: bool = False,
        topic_prefix: str | None = None,
        deep: bool = False,
    ) -> list[tuple]:
        """Semantic recall over facts (cosine on embeddings).

        ``include_beliefs`` (Giro 2, anti-sycophancy read-side): opt
        ``status='user_belief'`` rows — unverified USER assertions of fact —
        back into the result. NARROW by design: it un-hides beliefs only
        (orphaned/quarantined keep their own audit opt-in,
        ``include_orphaned``). Default False = beliefs stay out of the view,
        so the memory never serves an uncorroborated user claim back as
        truth unless the caller explicitly asks and can caveat it.

        ``deep`` (v14, archaeology mode): lift the AGE-based freshness hiding so
        dormant-but-true memories stay findable months/years later ("what did
        the client say in March?"). The integrity guards are NOT lifted: a
        future transaction time (tamper signal) and a ``valid_until``
        hard-expire stay excluded in every mode. Default OFF = byte-identical
        recall.

        Args:
            query: text query, embedded and matched against fact corpus.
            k: top-k results.
            topic: optional topic filter (SQL WHERE topic = ?).
            include_superseded: when False (default), filter out rows
                with ``superseded_by IS NOT NULL`` (cycle #78).
            exclude_legacy: when True, drop rows with
                ``status='legacy_unverified'`` BEFORE top-k ranking. Use
                this to prevent pre-cycle-109 unverified inheritance from
                being promoted as "memory" (cycle #109 S4-A,
                MemoryGraft-inspired defense).
            min_status: optional trust floor. Rows whose
                ``_STATUS_RANK[status] < _STATUS_RANK[min_status]`` are
                dropped before top-k. Raises ValueError if value is not in
                ``_STATUS_RANK``.

        Default behaviour stays retro-compatible: only the supersession
        filter is on by default (consistent with cycle #78 contract);
        provenance filters are opt-in.
        """
        _validate_min_status(min_status)
        # Robustezza (hunt 2026-06-04): k<=0 -> []. Senza guard, np.argsort(-sims)[:k]
        # con k negativo restituisce N-|k| righe (k=-1 = tutto tranne l'ultima) =
        # sversamento del corpus su un input caller-arithmetic o malevolo.
        if k <= 0:
            return []
        # S5 (F1 adversarial map 2026-07-10): a query with no tokens has no
        # intent — recall("") / recall("   ") used to return k spurious hits
        # scored against the empty-query vector, which a dossier renders as
        # "here is what I found for your (empty) search" = noise as an answer.
        # The honest result is [] (same contract as k<=0). Non-blank queries —
        # including SQL-ish / null-byte / injection text — are unaffected
        # (parameterized SQL + plain-text embedding already make them safe).
        if not (query or "").strip():
            return []
        # Recall must NEVER block on a cold/contended encode daemon (unlike a
        # save, it can't defer — it needs the query vector). Bound the query
        # encode; on overrun fall back to INSTANT keyword recall (same
        # (Fact, score) shape) instead of hanging on the in-process cold-load.
        q_emb = _encode_prepared_within_budget(
            embedding.as_query(query), _RECALL_ENCODE_BUDGET_S,
            thread_name="hippo-recall-encode",
        )
        if q_emb is None:
            # HIGH-1 (correctness-hunt #3, 2026-06-13): oversample so the
            # default-view filters below don't starve the result, then apply the
            # SAME three filters the warm cache/legacy paths enforce but
            # search_facts does not — otherwise the cold-encode path returns a
            # strictly larger, lower-trust set than a warm recall.
            kw = self.search_facts(
                query, limit=max(k * 4, k), topic=topic,
                include_superseded=include_superseded,
                exclude_legacy=exclude_legacy, min_status=min_status,
                include_orphaned=include_orphaned,  # hunt #3: honour audit opt-in
                include_beliefs=include_beliefs,    # Giro 2: same lesson as hunt #3
                tokenize=True,  # A4: multi-word queries must not degrade to []
                # FIX 2026-06-09 (audit#3-r3 R3): forward the tenant prefix so
                # the cold-encode keyword fallback stays scope-isolated — without
                # it a scoped recall under-returns AND can leak other tenants'
                # rows when the embed daemon is cold.
                topic_prefix=topic_prefix,
            )
            _now = time.time()

            def _passes_recall_view(f: Fact) -> bool:
                # (a) freshness cutoff — both warm paths hide stale-aged facts
                # (deep=archaeology lifts only the age part, integrity stays).
                if _fact_is_stale(
                    getattr(f, "last_verified_at", None), f.created_at, _now,
                    valid_until=getattr(f, "valid_until", None),
                    ignore_age=deep,
                ):
                    return False
                # (b) anti-laundering — unverified conversational_promotion.
                if not include_conversational and _is_unverified_conversational(f):
                    return False
                # (c) telemetry denylist — only on a generic (topic=None) recall.
                if topic is None and _is_telemetry_topic(getattr(f, "topic", None)):
                    return False
                return True

            kw = [f for f in kw if _passes_recall_view(f)]
            # Backlog recall-quality (audit 2026-06-14, conf 0.82): search_facts
            # ordina per created_at DESC (recency); il taglio [:k] sceglieva i k
            # piu' RECENTI, non i piu' RILEVANTI -> a corpus grande con >k match
            # il gold (token raro, magari vecchio) cadeva fuori dal top-k. Ri-rank
            # LESSICALE (BM25) prima del taglio: approssima la rilevanza che il
            # warm path ottiene dal cosine. Fail-soft: bm25 [] o errore -> ordine
            # recency invariato; i kw non in bm25 restano in coda (sort stabile).
            try:
                from .bm25_rank import bm25_fact_ids as _bm25_ids
                _bm = {
                    fid: i for i, fid in enumerate(
                        _bm25_ids(query, str(self.db_path), limit=max(k * 4, k))
                    )
                }
                if _bm:
                    kw.sort(key=lambda f: _bm.get(f.id, len(_bm)))
            except Exception:  # noqa: BLE001 — degrada con grazia alla recency
                pass
            # Osservabilita' (prima il degrado cold-encode era invisibile al
            # caller: solo un log dentro _encode_prepared_within_budget).
            self._recall_degraded_count = getattr(
                self, "_recall_degraded_count", 0,
            ) + 1
            kw = kw[:k]
            hits_2t = [(f, 0.0) for f in kw]
            # #2 default-ON prereq (audit round-2 2026-06-14): quando il fusion e'
            # ON, anche il ramo COLD guadagna il segnale entity-PPR (oltre al
            # BM25-reorder sopra) -> la garanzia "fusion attiva" vale su TUTTI i
            # path (cache hot-path, legacy SQL, cold), chiudendo l'asimmetria
            # cache-vs-cold (lezione SCAN-68) proprio nello scenario daemon-freddo
            # dove i segnali grafo/lessicali (cheap, no embedding) servono di piu'.
            # OFF -> _maybe_fuse_ppr e' un no-op (gated); il budget-thread (#1) lo
            # cappa, quindi un cold-recall non rischia il tail-latency del PPR.
            hits_2t = self._maybe_fuse_ppr(
                query, hits_2t, k, topic_prefix=topic_prefix, topic=topic,
                exclude_legacy=exclude_legacy, min_status=min_status,
                include_conversational=include_conversational)
            return self._attach_trust_signals(hits_2t) if trust_signals else hits_2t

        # Cycle #135 (2026-05-17): hot-path cache for the common case
        # ``topic=None``. We keep a pre-stacked numpy matrix + Fact list
        # for the whole live corpus and invalidate on store/delete.
        # The cosine step becomes one BLAS dot product against a
        # cached matrix — no per-row Python deserialize.
        #
        # The cache only handles the default-filter case (no topic, no
        # include_superseded). Any narrowing filter falls back to SQL
        # path where deserialize cost on a smaller M < N is acceptable.
        # Cycle #137: the cache pre-filters out orphaned rows (the
        # default-filter view is "live AND not orphaned"). If the
        # caller explicitly asks for orphaned facts (audit / undo),
        # we fall back to the legacy SQL path which can opt them in.
        cache_eligible = (
            topic is None
            and topic_prefix is None
            and not include_superseded
            and not include_orphaned
            # Giro 2: the corpus cache IS the default view (beliefs pre-filtered
            # at build time) — an include_beliefs query must take the legacy SQL
            # path, so the cache can never be poisoned with opt-in rows nor the
            # opt-in starved by a warm default cache.
            and not include_beliefs
            and not include_conversational
        )
        if cache_eligible:
            facts, matrix, lv, vu = self._get_corpus_cache()  # quadrupla ATOMICA
            if not facts:
                return []
            # ANN pre-narrowing (auto-on with faiss above the 100k gate,
            # ENGRAM_ANN_RECALL=0 opts out — _ann_recall_enabled):
            # restrict the corpus to the ANN candidate pool so the exact filters
            # / cosine / rerank below run on O(pool) not O(N). Byte-identical to
            # brute-force when OFF or below the gate (query_pool -> None). The
            # oversampled pool preserves the true top-k that survive the filters.
            if _ann_recall_enabled():
                try:
                    # background=True: never build inline — exact brute until
                    # the index for THIS corpus version is ready (iter 26).
                    _pool = self._ann_cache.query_pool(
                        matrix, q_emb, k, version=self._cache_version,
                        background=True)
                except Exception:  # noqa: BLE001 — faiss missing/broken -> exact brute
                    _pool = None
                if _pool is not None and len(_pool):
                    facts = [facts[i] for i in _pool]
                    matrix = matrix[_pool]
                    lv = lv[_pool]
                    vu = vu[_pool]
            # Status/legacy filters: bitmask on the cached facts list.
            keep_idx: list[int] | None = None
            if exclude_legacy or min_status is not None:
                _min_rank = (
                    _STATUS_RANK[min_status] if min_status is not None else -1
                )
                keep_idx = [
                    i for i, f in enumerate(facts)
                    if (
                        not (exclude_legacy and f.status == "legacy_unverified")
                        and _STATUS_RANK.get(f.status, 0) >= _min_rank
                    )
                ]
                if not keep_idx:
                    return []
                view_matrix = matrix[keep_idx]
                view_facts = [facts[i] for i in keep_idx]
                view_lv = lv[keep_idx]
                view_vu = vu[keep_idx]
            else:
                view_matrix = matrix
                view_facts = facts
                view_lv = lv
                view_vu = vu
            # v8 (2026-06-03) buco #3: cutoff freshness PRIMA del top-k, cosi'
            # i fatti stantii non occupano slot. Esclude i capability-claim
            # scaduti per eta (last_verified_at oltre half-life) — il fix del
            # caso A2A "prima funzionava". Maschera numpy VETTORIALE (non un
            # loop Python: preserva lo scaling sub-lineare cycle 135).
            # is_stale(floor=0.5) <=> age > half_life <=> base < now-half_life
            # (equivalenza algebrica esatta con freshness.decay_factor; il
            # legacy path sotto usa _fact_is_stale per-riga — non hot).
            # ANTI-SPOOF v8.1 (buco #3b): fresco SOLO nell'intervallo
            # [now-half_life, now]. Il bound superiore (view_lv <= now) e' il
            # fail-closed sul futuro — specchio vettoriale di _fact_is_stale:
            # un last_verified_at nel futuro (caller-spoofabile) e' escluso,
            # NON trattato come fresco.
            now = time.time()
            _fresh_after = now - _DEFAULT_HALF_LIFE_DAYS * 86400.0
            # v8 freshness (eta) AND v10 valid-time (hard-expire), in una sola
            # maschera vettoriale. view_vu==inf per i fatti senza scadenza
            # (vu > now sempre vero -> mai esclusi); un valid_until <= now li
            # toglie dal top-k a prescindere dall'eta. Specchio del per-riga
            # _fact_is_stale(valid_until=...) sui due path freddi.
            # v14 deep: l'archeologia toglie SOLO il bound inferiore d'eta;
            # anti-spoof (lv<=now) e hard-expire (vu>now) valgono in ogni modo.
            if deep:
                fresh_mask = (view_lv <= now) & (view_vu > now)
            else:
                fresh_mask = (
                    (view_lv >= _fresh_after) & (view_lv <= now) & (view_vu > now)
                )
            if not bool(fresh_mask.all()):
                fresh_idx = np.nonzero(fresh_mask)[0]
                if fresh_idx.size == 0:
                    return []
                view_matrix = view_matrix[fresh_idx]
                view_facts = [view_facts[i] for i in fresh_idx]
            # P0.2 (2026-06-09): optional mean-centering (de-anisotropy). Raw
            # cosine on these embeddings is anisotropic — every fact sits ~0.80
            # cos from any query, so the BEST match is hard to separate from the
            # rest (measured: an off-domain query scores ~0.81). Subtracting the
            # corpus mean before cosine restores discrimination. Measured on a
            # copy of the live corpus (25 labeled IT probes): R@10 0.84 -> 0.92,
            # previously-unretrievable facts 2 -> 0, R@1 unchanged. OPT-IN via
            # ENGRAM_RECALL_CENTERING (default OFF = byte-identical legacy
            # ranking, so existing tests / behaviour are untouched until flipped).
            import os as _os
            if _os.environ.get("ENGRAM_RECALL_CENTERING", "").strip().lower() in (
                "1", "on", "true", "yes",
            ):
                # Subtract the corpus mean, then RE-NORMALIZE so this is a true
                # cosine of the centered vectors — embedding.cosine_matrix is a
                # bare dot product (assumes unit-norm inputs), and centering
                # breaks the unit norm. (critic 2026-06-09: the first cut ranked
                # by an unnormalized centered dot, not cosine.)
                # ⚠ REFUTED at n=300 (sister-CLI bench scripts/bench_recall_self.py,
                # paired McNemar): the n=25 "win" (R@10 0.84->0.88) was NOISE; in
                # the realistic HARD regime centering HURTS recall (R@10
                # 0.777->0.697, p=0.0003). Kept ONLY as an opt-in A/B knob —
                # DEFAULT OFF, do NOT enable / promote. The real R@1 lever is the
                # cross-encoder reranker (engram/cross_encoder_rerank.py).
                _mu = matrix.mean(axis=0)  # global corpus mean (full, pre-filter)
                _qc = q_emb - _mu
                _qc = _qc / max(float(np.linalg.norm(_qc)), 1e-8)
                _mc = view_matrix - _mu
                _mc = _mc / np.clip(
                    np.linalg.norm(_mc, axis=1, keepdims=True), 1e-8, None
                )
                sims = embedding.cosine_matrix(_qc, _mc)
            else:
                sims = embedding.cosine_matrix(q_emb, view_matrix)
            # Robustezza: una riga embedding corrotta (NaN/inf da corruzione DB o
            # encode degenere) propaga NaN nello score. Mappa i non-finiti a -inf
            # (rank ultimo) ed ESCLUDILI dai risultati (come transcript_index).
            if not np.isfinite(sims).all():
                sims = np.where(np.isfinite(sims), sims, -np.inf)
            # Off-topic penalty (topic_priors): down-rank broadly-matching lessons/*
            # facts on task-style queries, after cosine/decay and BEFORE argsort.
            # No-op unless ENGRAM_TOPIC_PENALTY>0 (default off). (dormant moat wired 2026-06-20)
            sims = _apply_topic_penalty_to_sims(sims, view_facts, query)
            # P0.3 (2026-06-09): optional stage-2 cross-encoder rerank — the
            # real R@1 lever (verified on a copy, n=300 HARD, paired McNemar:
            # R@1 0.520->0.810, p<1e-5 — bench_rerank_n300_fast.py). OPT-IN,
            # default OFF: slice and ordering stay byte-identical to legacy.
            # When ON: widen the bi-encoder slice to the CE pool, rerank the
            # head, keep the cosine as the score, cut back to k.
            _rr_on = _rerank_enabled()
            _pool_n = max(k, _rerank_topn()) if _rr_on else k
            # (-score, fact.id) top-k: deterministic + row-order invariant, so
            # the ANN pool path returns EXACTLY the brute-force sequence.
            top_idx = _topk_deterministic(sims, _pool_n, view_facts)
            hits_2t = [
                (view_facts[i], float(sims[i]))
                for i in top_idx if np.isfinite(sims[i])
            ]
            if _rr_on and len(hits_2t) > 1:
                hits_2t = self._rerank_stage2(query, hits_2t, k)
            else:
                hits_2t = hits_2t[:k]
            hits_2t = self._maybe_fuse_ppr(
                query, hits_2t, k,
                exclude_legacy=exclude_legacy, min_status=min_status)
            # bump-on-recall (no open txn on this cache path -> safe to write).
            # deep = archaeology: a read of the PAST must not refresh
            # last_verified_at, or one time-travel query resurrects dormant
            # facts into the live default view (review 5-lenti C3).
            if not deep:
                self._bump_verified(hits_2t, now)
            # Fall-through into the trust-signal branch below.
            if not trust_signals:
                return hits_2t
            # else: drop to the post-hoc trust-signal attachment.
            return self._attach_trust_signals(hits_2t)

        # Legacy path: SQL WHERE (topic / include_superseded) + per-row
        # deserialize. Used for non-default filters.
        with self._connect() as conn:
            clauses: list[str] = []
            params: list[Any] = []
            if topic:
                clauses.append("topic = ?")
                params.append(topic)
            if topic_prefix:
                # B-1 scale: narrow to a tenant prefix at the DB level so the
                # cosine top-k competes only among the tenant's own rows
                # (complete recall, not oversample-bounded).
                # 2026-06-29: a half-open RANGE (topic >= p AND topic < p⁺)
                # drives idx_facts_topic (B-tree prefix scan, O(N_tenant)); the
                # old ``LIKE 'p%'`` could not use the index → full superseded_by
                # scan O(N_total) (measured 203ms→0.16ms @1M/10k tenants once
                # ANALYZE stats exist — multitenant_scan_v2.py). The range also
                # treats '_' as a LITERAL (no LIKE single-char glob), which is
                # exactly the prefix semantics — so no wildcard escaping needed.
                clauses.append("topic >= ? AND topic < ?")
                params.append(topic_prefix)
                params.append(_topic_prefix_upper(topic_prefix))
            if not include_superseded:
                clauses.append("superseded_by IS NULL")
            if not include_orphaned:
                # Cycle #137: hide rows scrubbed by L2 reconciler.
                # Cycle #138 (critic-fix, 2026-05-18): also hide
                # 'quarantined' rows on this legacy SQL branch — the
                # cache branch line ~572 already filters both; this
                # parallel path was missed in cycle 138 v1 and the
                # counterexample worker (job 1a80633751dc1459) found
                # the gap.
                # Giro 2: include_beliefs opts user_belief (and ONLY it) back
                # in; include_orphaned keeps its wider audit semantics (drops
                # the whole clause — everything visible), unchanged.
                _hidden = ("('orphaned', 'quarantined')" if include_beliefs
                           else "('orphaned', 'quarantined', 'user_belief')")
                clauses.append(f"status NOT IN {_hidden}")
            if not include_conversational:
                # Anti-laundering (2026-06-03): simmetrico al cache fast-path.
                # Esclude le promozioni conversational non ancora verificate dal
                # recall di default; include_conversational=True le riammette (opt-in).
                clauses.append(
                    "NOT (writer_role = 'conversational_promotion' "
                    "AND status != 'verified')"
                )
            # SCAN-68 (audit 2026-06-02, NONNA): denylist telemetria SOLO sul
            # recall generico (topic=None), come il cache fast-path -> chiude
            # l'asimmetria cache-vs-legacy trovata dall'audit-agente. Con un
            # topic esplicito NON si applica (chi chiede 'bus/x' lo vuole).
            if topic is None:
                clauses.extend(_TELEMETRY_DENYLIST_CLAUSES)
            # Cycle 171 (2026-05-22) defensive shape filter — see
            # _get_corpus_cache comment for rationale. SQL-side filter
            # avoids per-row Python deserialize, preserving the cycle
            # 135 sub-linear scaling on this legacy path too.
            clauses.append("length(embedding) = ?")
            params.append(embedding.expected_embedding_bytes())
            # v9 (Sorella C): isola lo spazio di embedding al modello attivo
            # (simmetrico al cache fast-path). COALESCE -> riga legacy (NULL)
            # == baseline storico. Blocca il poisoning silenzioso same-dim.
            clauses.append("COALESCE(embedding_model, ?) = ?")
            params.append(_LEGACY_EMBEDDING_MODEL)
            params.append(embedding.model_signature())
            # topic_prefix path: force idx_facts_topic so the half-open range is
            # an O(N_tenant) B-tree prefix scan regardless of ANALYZE stats —
            # without the hint SQLite picks idx_facts_superseded_by → O(N_total)
            # full scan (measured 100ms→0.18ms @500k rows, no ANALYZE needed —
            # arch-lab/sistema/multitenant_scan_v2.py).
            sql = ("SELECT * FROM facts INDEXED BY idx_facts_topic"
                   if topic_prefix else "SELECT * FROM facts")
            if clauses:
                sql += " WHERE " + " AND ".join(clauses)
            rows = conn.execute(sql, tuple(params)).fetchall()
            if not rows:
                return []
            if exclude_legacy or min_status is not None:
                rows = [
                    r for r in rows
                    if _row_passes_status_filter(
                        r, exclude_legacy=exclude_legacy,
                        min_status=min_status,
                    )
                ]
                if not rows:
                    return []
            # v8 (2026-06-03) buco #3: cutoff freshness anche sul legacy path
            # (simmetria col cache fast-path sopra, lezione SCAN-68). Filtra le
            # righe stantie PRIMA di np.stack/top-k. Lettura difensiva su
            # last_verified_at (None su righe pre-v8 -> coalesce a created_at).
            _now = time.time()

            def _row_lv(r: sqlite3.Row) -> float | None:
                try:
                    return r["last_verified_at"]
                except (IndexError, KeyError):
                    return None

            def _row_vu(r: sqlite3.Row) -> float | None:
                # v10 valid-time: defensive su righe pre-v10 (None = no expiry).
                try:
                    return r["valid_until"]
                except (IndexError, KeyError):
                    return None

            rows = [
                r for r in rows
                if not _fact_is_stale(
                    _row_lv(r), r["created_at"], _now, valid_until=_row_vu(r),
                    ignore_age=deep,
                )
            ]
            if not rows:
                return []
            # Batch-deserialize: one np.frombuffer over the joined blobs instead
            # of a per-row stack — 3.1-3.7x faster (the per-query O(N_tenant)
            # deserialize is the dominant cost on the scoped path after the
            # lookup-index fix: 374ms->100ms @100k rows,
            # arch-lab/sistema/deser_bench.py). Identical result (np.array_equal);
            # the SQL ``length(embedding) = ?`` filter above guarantees
            # uniform-length blobs (reshape safe) and ``corpus`` is read-only here
            # (cosine dot only), so frombuffer's read-only view is fine.
            corpus = np.frombuffer(
                b"".join(r["embedding"] for r in rows), dtype=np.float32
            ).reshape(len(rows), -1)
            sims = embedding.cosine_matrix(q_emb, corpus)
            # Robustezza non-finite (vedi cache-path): escludi righe NaN/inf.
            if not np.isfinite(sims).all():
                sims = np.where(np.isfinite(sims), sims, -np.inf)
            # Off-topic penalty (topic_priors) — same wiring as the cache fast-path
            # (SCAN-68: cache-vs-legacy asymmetry is a bug). No-op unless enabled.
            sims = _apply_topic_penalty_to_sims(sims, rows, query)
            # P0.3: same opt-in rerank wiring as the cache fast-path above —
            # SCAN-68 lesson: cache-vs-legacy asymmetries are audit findings.
            _rr_on = _rerank_enabled()
            _pool_n = max(k, _rerank_topn()) if _rr_on else k
            # same deterministic tie-break as the cache fast-path (SCAN-68:
            # cache-vs-legacy asymmetries are audit findings).
            top_idx = _topk_deterministic(sims, _pool_n, rows)
            hits_2t = [
                (self._row(rows[i]), float(sims[i]))
                for i in top_idx if np.isfinite(sims[i])
            ]
        # P0.3: rerank OUTSIDE the read txn (rerank_candidates opens its own
        # sqlite connection on the same file — keep it out of the with-block).
        if _rr_on and len(hits_2t) > 1:
            hits_2t = self._rerank_stage2(query, hits_2t, k)
        else:
            hits_2t = hits_2t[:k]
        hits_2t = self._maybe_fuse_ppr(
            query, hits_2t, k, topic_prefix=topic_prefix, topic=topic,
            exclude_legacy=exclude_legacy, min_status=min_status,
            include_conversational=include_conversational)
        # bump-on-recall (outside the read txn -> no nested connection).
        # deep = archaeology, read-only w.r.t. freshness (review 5-lenti C3).
        if not deep:
            self._bump_verified(hits_2t, _now)
        # Cycle #117: optional trust signals — attach a live verdict
        # (trusted/stale/contested/obsolete/unverified) to each hit so
        # the caller (LLM, dashboard, tests) sees both content and
        # meta-confidence in one shot. Backwards-compatible: default
        # False returns 2-tuples; True returns 3-tuples.
        if not trust_signals:
            return hits_2t
        from .contradiction import ContradictionStore
        from .trust_signal import compute_trust_signal
        store = ContradictionStore(self.db_path)
        return [
            (f, sim, compute_trust_signal(
                f, self, contradiction_store=store,
            ))
            for f, sim in hits_2t
        ]

    def _rerank_stage2(
        self, query: str, hits_2t: list[tuple], k: int,
    ) -> list[tuple]:
        """P0.3: re-order the bi-encoder shortlist with a cross-encoder.

        Only the first ``_rerank_topn()`` candidates are SCORED — the CE cost
        is per-pair and ``rerank_candidates`` scores every pair it receives
        (its ``top_n`` only caps the RETURNED list); the tail keeps bi-encoder
        order. The returned score stays the ORIGINAL cosine, so downstream
        thresholds and trust_signals remain valid. HARD fallback: on ANY
        error the bi-encoder order is returned unchanged (never an id-sort;
        the primitive's scorer-error path is order-preserving since the
        2026-06-09 tie-break fix).

        Length guard (comparative LongMemEval 2026-06-10): the CE truncates at
        512 tokens, so on a pool of LONG documents it scores only the head and
        scrambles an already-good bi-encoder order. When the pool's median
        proposition length exceeds ``_rerank_max_doc_chars()`` the CE is
        skipped — not even loaded — and the bi-encoder order stands.
        """
        from .cross_encoder_rerank import rerank_candidates
        if _RERANK_BREAKER["tripped"]:
            return hits_2t[:k]  # systematic overruns → stop paying the budget
        pool = hits_2t[:_rerank_topn()]
        tail = hits_2t[len(pool):]
        _cap = _rerank_max_doc_chars()
        if _cap and pool:
            _lens = sorted(len(getattr(f, "proposition", "") or "")
                           for f, _ in pool)
            _median = _lens[len(_lens) // 2]
            if _median > _cap:
                return hits_2t[:k]  # docs out of CE window — keep bi-encoder
        by_id = {f.id: (f, sim) for f, sim in pool}
        # Circuit-breaker (2026-06-13): the CE COLD load is ~33s and the steady
        # predict ~1.7s; under CPU contention the cold-load was the 10-min recall
        # hang. The try/except below catches scorer ERRORS but NOT a hang, so run
        # load+score in a daemon thread joined with a wall-clock budget. On
        # overrun keep the bi-encoder order (already valid) and let the worker
        # finish warming the model in the background — the NEXT query reranks.
        _budget = _recall_rerank_budget_s()
        # Cold-start (2026-06-14): while the CE is not resident, cap THIS query's
        # wait to the small cold budget instead of the full ~3s — the daemon
        # worker below keeps the load running, so a later query reranks once the
        # CE is warm. Removes the recall p95 3.1s tail WITHOUT skipping rerank
        # when a scorer is already available (keeps the injected-scorer paths
        # valid). Once _RERANKER is resident the steady predict fits the budget.
        _was_ready = _reranker_ready()
        if not _was_ready:
            _budget = min(_budget, _rerank_cold_budget_s())
        if _budget <= 0:
            try:
                scorer = _load_reranker()
                ranked = rerank_candidates(
                    query, [f.id for f, _ in pool],
                    semantic_db=self.db_path, scorer=scorer, top_n=len(pool),
                )
            except Exception:  # noqa: BLE001 — recall must NEVER break when ON
                return hits_2t[:k]
        else:
            _box: dict[str, Any] = {}

            def _work() -> None:
                # Exception (not BaseException): a scorer/load failure is always
                # an Exception; SystemExit/KeyboardInterrupt don't reach a daemon
                # worker thread, and catching them here would only mask shutdown.
                try:
                    scorer = _load_reranker()
                    _box["ranked"] = rerank_candidates(
                        query, [f.id for f, _ in pool],
                        semantic_db=self.db_path, scorer=scorer, top_n=len(pool),
                    )
                except Exception as exc:  # noqa: BLE001 — surfaced below
                    _box["err"] = exc

            _t = threading.Thread(target=_work, name="hippo-rerank", daemon=True)
            _t.start()
            _t.join(_budget)
            if _t.is_alive():
                if _was_ready:
                    _LOG.warning(
                        "rerank exceeded %.1fs budget → keeping bi-encoder "
                        "order (steady overrun; counts toward the breaker)",
                        _budget,
                    )
                    _rerank_breaker_overrun()
                else:
                    # F1 C1: cold overrun = CE still warming = transient by
                    # definition. Never counts toward the steady trip; only
                    # the generous cold bound (never-warms pathology) does.
                    _LOG.warning(
                        "rerank cold-load exceeded %.2fs cold budget → keeping "
                        "bi-encoder order (CE warming in background; cold "
                        "overruns do not trip the steady breaker)", _budget,
                    )
                    _rerank_breaker_cold_overrun()
                return hits_2t[:k]
            if "err" in _box:
                return hits_2t[:k]  # scorer error → bi-encoder order
            ranked = _box.get("ranked")
            _RERANK_BREAKER["consecutive"] = 0  # in-budget → transient, re-arm
            _RERANK_BREAKER["cold"] = 0         # CE answered → warm again
        if not ranked:
            return hits_2t[:k]
        reordered = [by_id[fid] for fid, _ce in ranked if fid in by_id]
        # Defensive: re-attach pool items the primitive dropped (ids missing
        # from the DB) so a hit never silently disappears from the result.
        seen = {f.id for f, _ in reordered}
        reordered += [(f, s) for f, s in pool if f.id not in seen]
        return (reordered + tail)[:k]

    def _recall_entity_store(self) -> Any:
        """Lazy EntityStore over the same data dir as this semantic db, for the
        opt-in PPR-fusion recall path. Built once per SemanticMemory instance."""
        es = self._recall_es
        if es is None:
            from .entity_kg import EntityStore
            from .entity_populate import entity_kg_path_for
            es = EntityStore(db_path=entity_kg_path_for(self.db_path))
            self._recall_es = es
        return es

    def set_reconcile_judge(self, judge) -> None:
        """Wire a semantic NLI judge (semantic_conflict.RelationJudge) used by
        reconcile-on-write. The storage layer never builds an LLM itself — the
        application (which holds one) injects the judge here, keeping the layers
        decoupled. None (the default) -> the lexical heuristic, unchanged. Validated:
        ~4× conflict-recall at no precision cost (benchmark/reconcile_truth_maintenance)."""
        self._reconcile_judge = judge

    def reconcile_new_fact(self, fact, *, auto_supersede: bool = False, judge=None,
                           require_evidence: bool = False,
                           protect_evidenced: bool = False) -> dict:
        """P1 truth-reconciliation on a just-stored fact: find shared-entity
        update candidates and reconcile. Fail-safe default (``auto_supersede=
        False``): contest, never supersede. Wired into ``store()`` behind
        ENGRAM_RECONCILE_ON_WRITE; also callable directly. Best-effort.

        ``judge`` (a semantic_conflict.RelationJudge) upgrades conflict confirmation from
        the lexical heuristic to NLI — catches paraphrase/antonym value-conflicts the
        lexical path misses AND rejects complementary same-entity facts. Pass an
        LLMRelationJudge for the semantic path; None keeps the (default) lexical behavior."""
        from .contradiction import ContradictionStore
        from .truth_reconciliation import reconcile_against_corpus
        es = self._recall_entity_store()
        cs = ContradictionStore(self.db_path)
        return reconcile_against_corpus(
            self, fact, es, contradiction_store=cs, now=time.time(),
            auto_supersede=auto_supersede, judge=judge,
            require_evidence=require_evidence, protect_evidenced=protect_evidenced)

    def _auto_confirm_source_trust(self, fact) -> None:
        """Feed the source-trust consistency channel from same-topic agreement
        (opt-in, ENGRAM_SOURCE_AUTO_CONFIRM). A fact whose proposition restates a LIVE
        same-topic fact from a DIFFERENT cited source is corroboration; a different
        proposition from another source is a divergence. ``auto_confirm_agreement``
        picks the accepted value by INDEPENDENT witnesses (a write-majority cartel of
        copies collapses to one), confirms its sources, contradicts the divergent.

        Keys on the TOPIC as the subject and the exact PROPOSITION as the value: exact
        corroboration is handled; paraphrase agreement needs the NLI judge (follow-up).
        One vote per cited source (agent-authored facts share the 'user' fallback, so a
        single author can never self-confirm). Best-effort, consistency channel only."""
        from .source_trust import (
            auto_confirm_agreement,
            canonical_source,
            get_book,
            independence_deconfounded,
            independence_enabled,
        )
        topic = (getattr(fact, "topic", "") or "").strip()
        if not topic or _is_telemetry_topic(topic):
            return
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM facts WHERE topic = ? AND superseded_by IS NULL "
                "AND status NOT IN ('orphaned', 'quarantined', 'user_belief') "
                "ORDER BY created_at DESC LIMIT 200", (topic,)).fetchall()
        reports: dict[str, str] = {}
        for r in rows:
            f = self._row(r)
            src = canonical_source(getattr(f, "verified_by", None))
            prop = (getattr(f, "proposition", "") or "").strip()
            if src and prop and src not in reports:   # latest proposition per source
                reports[src] = prop
        if len({s for s in reports if s != "user"}) < 2:
            return          # corroboration needs >=2 distinct CITED sources
        auto_confirm_agreement(
            get_book(self.db_path), topic, reports,
            independence=independence_enabled(),
            deconfound=independence_deconfounded())

    def _maybe_fuse_ppr(
        self, query: str, hits: list[tuple[Fact, float]], k: int,
        *, topic_prefix: str | None = None, topic: str | None = None,
        exclude_legacy: bool = False, min_status: str | None = None,
        include_conversational: bool = False,
    ) -> list[tuple[Fact, float]]:
        """Opt-in (ENGRAM_PPR_FUSION): RRF-fuse query-auto-seeded entity-PPR AND
        BM25-lexical into the result AFTER the CE-rerank (the 3-signal fusion;
        fusion×rerank fix 2026-06-14).

        Fusing BEFORE the rerank let the text-based CE drown a graph/lexical fact
        whose text is far from the query (cosine ~0) — exactly the multi-hop /
        exact-token case PPR + BM25 exist to rescue. Running the fusion on the
        ALREADY-reranked list means extra-only facts never pass through the CE
        scorer: they enter purely via RRF against the CE order. PPR (HippoRAG-2
        gap) + BM25 (Zep gap) are each their own RRF signal. Capped at k.
        Fail-soft: any error / no extra signals → unchanged."""
        if not _ppr_fusion_enabled() or not query or not hits:
            return hits
        # #3 default-ON prereq (audit round-2): su corpus PICCOLI il bi-encoder +
        # CE bastano e i 2 DB-open + il graph-build del PPR sono puro overhead.
        # DEFAULT 50 (col flip default-ON 2026-06-15): sotto 50 fatti niente
        # fusione. ENGRAM_PPR_FUSION_FLOOR=0 disabilita il floor (per i test che
        # vogliono la fusione su corpus minimi). len() sulla corpus-cache (O(1)
        # cache-hit sul warm path). Fail-soft: in dubbio si fonde.
        _floor = int(os.environ.get("ENGRAM_PPR_FUSION_FLOOR", "50"))
        if _floor > 0:
            try:
                if len(self._get_corpus_cache()[0]) < _floor:
                    return hits
            except Exception:  # noqa: BLE001 — fail-soft: in dubbio, fondi
                pass

        # #1 default-ON prereq (audit round-2 2026-06-14): the fusion body —
        # entity-PPR power iteration (uncapped nx.pagerank) + BM25 + RRF — runs on
        # a daemon thread joined for a wall-clock budget, the SAME guard the
        # CE-rerank already uses (_rerank_stage2). On overrun the fusion is skipped
        # and the already-reranked hits are kept (= the OFF behaviour), so a
        # future default-ON can never add a tail-latency hang the OFF path lacks.
        # Fail-soft on any error. ENGRAM_PPR_FUSION_BUDGET_S=0 runs it
        # synchronously (no cap) — for an accurate latency micro-bench.
        def _fuse() -> list[tuple[Fact, float]]:
            from .bm25_rank import bm25_fact_ids
            from .ppr_seed import fuse_dense_and_ppr, ppr_seeded_fact_ids
            ppr_ids = ppr_seeded_fact_ids(query, self._recall_entity_store())
            bm25_ids = bm25_fact_ids(query, self.db_path)
            if not ppr_ids and not bm25_ids:
                return hits
            # live_only=True: gli extra-id PPR/BM25 sono fetchati col MEDESIMO
            # filtro live del path principale — un fatto superseded/orphaned/
            # quarantined (ritrattato) non viene resuscitato dal fusion (stesso
            # leak chiuso per anchor/entity in HIGH-2). I dense hits NON passano
            # da fetch_fact (sono gia' nel pool, gia' filtrati), quindi restano.
            # protect_top=k//2 (dense-floor 2026-07-07): la testa CE-reranked è
            # intoccabile, gli extra PPR/BM25 competono solo per la coda —
            # misurato: senza floor, a k=12 su grafo hub-dominated la fusione
            # DIMEZZAVA la copertura evidence (16/61 → 8/61, fact a2217252f9ad).
            fused = fuse_dense_and_ppr(
                hits, [ppr_ids, bm25_ids],
                lambda fid: self.get(fid, live_only=True),
                protect_top=max(1, k // 2),
            )
            # B-1 multi-tenant (CI 2026-06-15, flip default-ON): PPR/BM25
            # ripescano fact-id dal corpus INTERO, ignorando lo scope che il
            # SQL/cache path ha gia' applicato ai dense hits. Senza riapplicare
            # qui gli STESSI predicati di scope, il fusion default-ON
            # re-introduce fatti fuori-tenant (regressione presa dalla CI:
            # test_recall_topic_prefix_narrows_at_db_level).
            if topic_prefix:
                fused = [(f, s) for f, s in fused
                         if (f.topic or "").startswith(topic_prefix)]
            if topic is not None:
                fused = [(f, s) for f, s in fused if f.topic == topic]
            # Audit R3 #3: il fusion ripesca dal corpus INTERO ignorando i filtri
            # di PROVENIENZA che il SQL/cache path applica ai dense hits. Senza
            # riapplicarli, default-ON re-introduce legacy_unverified /
            # conversational-non-verificati / sotto-min_status che il recall
            # aveva escluso dal trust-floor.
            if exclude_legacy:
                fused = [(f, s) for f, s in fused
                         if f.status != "legacy_unverified"]
            if min_status is not None:
                _mr = _STATUS_RANK[min_status]
                fused = [(f, s) for f, s in fused
                         if _STATUS_RANK.get(f.status, 0) >= _mr]
            if not include_conversational:
                fused = [(f, s) for f, s in fused
                         if not _is_unverified_conversational(f)]
            return fused[:k]

        _budget = _ppr_fusion_budget_s()
        if _budget <= 0.0:  # 0 = no cap, synchronous (accurate bench)
            try:
                return _fuse()
            except Exception:  # noqa: BLE001 — recall must never break
                return hits

        _box: dict[str, Any] = {}

        def _work() -> None:
            try:
                _box["fused"] = _fuse()
            except Exception as exc:  # noqa: BLE001 — surfaced below
                _box["err"] = exc

        _t = threading.Thread(target=_work, name="hippo-ppr-fusion", daemon=True)
        _t.start()
        _t.join(_budget)
        if _t.is_alive():
            _LOG.warning(
                "PPR fusion exceeded %.2fs budget → keeping reranked order "
                "(graph/lexical signals skipped this query)", _budget,
            )
            return hits
        if "err" in _box:
            return hits  # fail-soft: recall must never break on the opt-in path
        return _box.get("fused", hits)

    # ----------------------------------------------------------------
    # Cycle 161 (2026-05-19) — hybrid recall (semantic + keyword overlap).
    # Empirical motivation: cycle 160 bench (fact 9379c8141a3e) on prod
    # corpus measured semantic-only TPR@5 = 40%; with the same 3-query
    # subset, a keyword-overlap pass over the cycle-160 ``trigger_keywords``
    # field reached TPR = 80% (fact 7defa6248327). This method combines
    # both signals so callers don't have to pick one.
    # ----------------------------------------------------------------

    # Cycle 166 (2026-05-19): query expansion synonym dictionary.
    # Catches OOD paraphrase queries by expanding query-side tokens to
    # commonly-co-occurring siblings BEFORE keyword overlap is computed.
    # No LLM dependency. Italian↔English bridging + math/tech jargon.
    # Keep small (high precision) — every entry pays a recall-side cost.
    _QUERY_SYNONYMS: dict[str, list[str]] = {
        "factorial":      ["factorial", "fattoriale"],
        "prime":          ["prime", "primo"],
        "power":          ["power", "potenza", "exponent"],
        "perfect":        ["perfect", "perfetta"],
        "equation":       ["equation", "equazione"],
        "robustness":     ["robustness", "resilience", "reliability"],
        "hypothesis":     ["hypothesis", "claim", "assumption"],
        "invalid":        ["invalid", "wrong", "incorrect", "false"],
        "injected":       ["injected", "injection", "inject"],
        "prior":          ["prior", "previous", "past"],
        "knowledge":      ["knowledge", "memory", "fact"],
        "database":       ["database", "sqlite", "db", "store"],
        "blob":           ["blob", "bytes", "buffer", "embedding"],
        "malformed":      ["malformed", "corrupted", "broken", "invalid"],
        "byte":           ["byte", "bytes", "buffer"],
        "length":         ["length", "size", "len"],
        "element":        ["element", "item", "row"],
        "number theory":  ["number theory", "modular arithmetic", "diophantine"],
    }

    def _expand_query_tokens(self, q_tokens: set[str]) -> set[str]:
        """Cycle 166: expand query tokens with synonyms from
        ``_QUERY_SYNONYMS``. Each token's synonyms are added to the
        set; the original token is preserved. Returns the union.
        """
        expanded: set[str] = set(q_tokens)
        for tok in list(q_tokens):
            for syns in self._QUERY_SYNONYMS.values():
                if tok in syns:
                    expanded.update(syns)
        return expanded

    def recall_hybrid(
        self, query: str, k: int = 5,
        *,
        semantic_weight: float = 0.6,
        candidate_multiplier: int = 3,
        expand_query: bool = True,
        exclude_legacy: bool = False,
        min_status: str | None = None,
    ) -> list[tuple]:
        """Hybrid recall: semantic cosine + keyword overlap re-rank.

        Pulls a candidate pool of ``k * candidate_multiplier`` via the
        existing semantic ``recall`` (so we benefit from the cycle #135
        corpus cache + every status / supersession filter), then re-ranks
        by ``semantic_weight * cosine + (1 - semantic_weight) * kw_overlap``
        where ``kw_overlap`` = (#tokens shared between the query and the
        fact's ``trigger_keywords``) / max(1, #unique-query-tokens).
        Both signals live in [0, 1], so the combo is a valid score.

        Defaults follow fact 7defa6248327:
          - ``semantic_weight=0.6`` — keeps semantic dominant so we still
            surface facts without ``trigger_keywords`` populated.
          - ``candidate_multiplier=3`` — pool of 15 candidates by default,
            wide enough to re-rank without paying the full corpus.

        Returns ``list[tuple[Fact, float]]`` (same shape as ``recall``).
        Empty/whitespace ``query`` returns ``[]`` immediately.
        """
        q = (query or "").strip()
        if not q:
            return []
        pool_k = max(k, k * int(max(1, candidate_multiplier)))
        # audit#3-r3 R19: forward provenance filters to the candidate pool so
        # legacy_unverified rows can be excluded BEFORE re-ranking — previously
        # recall_hybrid had no such knob and silently let them leak in. Defaults
        # (False / None) preserve parity with recall, so existing callers are
        # unaffected.
        candidates = self.recall(
            query, k=pool_k,
            exclude_legacy=exclude_legacy, min_status=min_status,
        )
        if not candidates:
            return []
        w = max(0.0, min(1.0, float(semantic_weight)))
        q_tokens = {t.lower() for t in q.replace(",", " ").split() if len(t) > 2}
        denom = max(1, len(q_tokens))
        # Cycle 166: synonym-expanded query tokens for kw overlap path.
        # Denominator stays = original query size so a per-token max-overlap
        # of 1.0 is preserved (synonyms boost recall, not over-score).
        q_tokens_expanded = (
            self._expand_query_tokens(q_tokens) if expand_query else q_tokens
        )
        # Audit R3 #13: i fatti che la fusion (in recall) ha SALVATO entrano nel
        # pool con cos_sim==0.0 (PPR/BM25, non cosine). Il termine w*cos li
        # azzererebbe e il re-rank li ri-seppellirebbe — l'OPPOSTO di cio' per cui
        # la fusion esiste. recall_hybrid non vede il segnale PPR/BM25 che li ha
        # salvati, quindi assegna loro il cosine MEDIANO del pool ("rilevanza
        # tipica"): competono coi dense mediani invece di collassare a 0, senza
        # essere trattati come il match migliore.
        _pos_cos = sorted(c for _, c in candidates if c > 0.0)
        if _pos_cos:
            _m = len(_pos_cos)
            _fused_floor = (_pos_cos[_m // 2] if _m % 2 else
                            0.5 * (_pos_cos[_m // 2 - 1] + _pos_cos[_m // 2]))
        else:
            _fused_floor = 0.0
        scored: list[tuple] = []
        for fact, cos_sim in candidates:
            kw_tokens: set[str] = set()
            for kw in (fact.trigger_keywords or []):
                kw_tokens.update(
                    t.lower() for t in kw.replace(",", " ").split() if len(t) > 2
                )
            overlap = len(q_tokens_expanded & kw_tokens) / denom
            # Cycle 164 (2026-05-19): add applicable_when token overlap to
            # kw signal. The field stores a one-sentence condition that
            # is often more semantic than the bag-of-keywords. A separate
            # overlap term keeps it bounded and weighted the same as
            # trigger_keywords (additive cap at 1.0). Empirical motivation:
            # cycle 162 rule-based trigger_keywords miss semantic
            # paraphrase; applicable_when can rescue when curated.
            aw_text = (fact.applicable_when or "").lower()
            aw_tokens = {
                t for t in aw_text.replace(",", " ").split() if len(t) > 2
            }
            aw_overlap = (
                len(q_tokens_expanded & aw_tokens) / denom if aw_tokens else 0.0
            )
            kw_signal = min(1.0, overlap + aw_overlap)
            eff_cos = float(cos_sim) if cos_sim > 0.0 else _fused_floor
            score = w * eff_cos + (1.0 - w) * kw_signal
            scored.append((fact, score))
        scored.sort(key=lambda t: -t[1])
        return scored[:k]

    def topics_for_query(self, query: str, k: int = 5) -> dict[str, float]:
        """FORGIA pezzo #180: schema priming primitive.

        Returns ``{topic: weight}`` over the top-K facts most similar
        to ``query``. Weights are normalized to sum to 1.0 (or empty
        dict when memory has no facts). Each fact's contribution is
        proportional to ``max(similarity, 0) * confidence`` — so a
        confident fact about an off-topic concept doesn't dominate
        the distribution if the similarity is weak.

        Inspired by Preston & Eichenbaum 2013: prefrontal cortex
        pre-activates schemas relevant to the upcoming task before
        the hippocampus retrieves specific memories.
        """
        hits = self.recall(query, k=k)
        if not hits:
            return {}
        weights: dict[str, float] = {}
        for fact, sim in hits:
            contrib = max(0.0, float(sim)) * float(fact.confidence)
            if contrib <= 0.0:
                continue
            weights[fact.topic] = weights.get(fact.topic, 0.0) + contrib
        total = sum(weights.values())
        if total <= 0.0:
            return {}
        return {t: w / total for t, w in weights.items()}

    def search_facts(
        self, query: str, *, limit: int = 20,
        topic: str | None = None,
        include_superseded: bool = False,
        exclude_legacy: bool = False,
        min_status: str | None = None,
        tokenize: bool = False,
        require_all_tokens: bool = False,
        topic_prefix: str | None = None,
        include_orphaned: bool = False,
        include_beliefs: bool = False,
    ) -> list[Fact]:
        """FORGIA pezzo #203: keyword/substring search over `proposition`.

        ``include_beliefs`` (Giro 2): opt ``user_belief`` rows back in — same
        narrow semantics as :meth:`recall`, honoured here too so the keyword
        surface (and recall's cold-encode fallback, which delegates here) can
        never become a back-door asymmetry (the cycle-138 lesson).

        Distinct from :meth:`recall` (semantic / cosine on embedding):
        this is a SQL LIKE on the proposition text, case-insensitive.
        Empty query returns the most-recent facts (capped by `limit`).
        Optional `topic` filter narrows to a specific topic.

        Cycle #109 S4-A: optional ``exclude_legacy`` and ``min_status``
        provenance filters (same semantics as :meth:`recall`). Filter
        runs in SQL WHERE — no Python post-filter pass needed since
        there's no top-k cosine step here.
        """
        _validate_min_status(min_status)
        q = (query or "").strip()
        with self._connect() as conn:
            sql = "SELECT * FROM facts"
            params: list[Any] = []
            clauses: list[str] = []
            if q:
                # Multi-word matching (audit 2026-06-08 + 2026-06-13). A direct
                # phrase LIKE returns [] unless the WHOLE query appears as a
                # contiguous substring — so `hippo_facts_search "recall rerank
                # circuit breaker"` found nothing even with facts containing all
                # those words (Aurelio hit this live). Two token modes:
                #   require_all_tokens=True → AND across tokens (precision: every
                #       token present somewhere). Used by the hippo_facts_search
                #       tool as its first pass.
                #   tokenize=True           → OR across tokens (recall: any token).
                #       Used by recall's cold/contended keyword fallback AND as the
                #       tool's OR-fallback when AND yields nothing.
                # Default (both False) stays exact-substring for back-compat.
                _multi = tokenize or require_all_tokens
                toks = [t for t in q.lower().split() if len(t) >= 2] if _multi else []
                if len(toks) > 1:
                    _join = " AND " if require_all_tokens else " OR "
                    clauses.append(
                        "(" + _join.join(
                            "LOWER(proposition) LIKE ? ESCAPE '\\'" for _ in toks
                        ) + ")"
                    )
                    # HIGH-3: escape LIKE wildcards so a token like 'node_engine'
                    # matches literally, not as a single-char glob.
                    params.extend(f"%{_like_escape_literal(t)}%" for t in toks)
                elif len(toks) == 1:
                    # Critic counterexample (2026-06-13): a multi-word query where
                    # only ONE token survives the len>=2 filter (e.g. "5 model",
                    # "c api", "R lang") must match THAT token, NOT the whole-phrase
                    # substring — otherwise it collapses back to the original bug
                    # (`%5 model%` finds nothing). The dispatcher's split()>1
                    # fallback gate and this >=2 filter disagreed on token count.
                    clauses.append("LOWER(proposition) LIKE ? ESCAPE '\\'")
                    params.append(f"%{_like_escape_literal(toks[0])}%")
                else:
                    # No usable token (all <2 chars, or single-word query) —
                    # exact-substring on the raw query (back-compat default).
                    clauses.append("LOWER(proposition) LIKE ? ESCAPE '\\'")
                    params.append(f"%{_like_escape_literal(q.lower())}%")
            if topic_prefix:
                # B-1 scale: narrow to the tenant prefix at the DB level (escape
                # '_'/'%', LIKE globs that ids may contain).
                clauses.append("topic LIKE ? ESCAPE '\\'")
                params.append(_like_escape_literal(topic_prefix) + "%")
            if topic:
                clauses.append("topic = ?")
                params.append(topic)
            if not include_superseded:
                clauses.append("superseded_by IS NULL")
            # Cycle #138 (critic-fix, 2026-05-18): search_facts must
            # also hide gate-flagged rows by default. Previously this
            # path was a back-door that surfaced 'quarantined' rows
            # through hippo_facts_search even when the recall hot-path
            # had been patched. Parity with recall's legacy SQL branch.
            # include_orphaned (audit/undo visibility, save-recall hunt #3): when
            # True surface orphaned/quarantined rows — parity with recall's warm
            # legacy branch, so the cold-encode fallback honours the same opt-in
            # instead of silently returning zero hidden rows.
            if not include_orphaned:
                # Giro 2: include_beliefs un-hides user_belief only (parity
                # with recall's legacy branch); include_orphaned keeps its
                # wider audit semantics unchanged.
                clauses.append(
                    "status NOT IN ('orphaned', 'quarantined')"
                    if include_beliefs else
                    "status NOT IN ('orphaned', 'quarantined', 'user_belief')"
                )
            if exclude_legacy:
                clauses.append("status != 'legacy_unverified'")
            if min_status is not None:
                allowed = [
                    s for s, r in _STATUS_RANK.items()
                    if r >= _STATUS_RANK[min_status]
                ]
                placeholders = ",".join("?" for _ in allowed)
                clauses.append(f"status IN ({placeholders})")
                params.extend(allowed)
            if clauses:
                sql += " WHERE " + " AND ".join(clauses)
            sql += " ORDER BY created_at DESC LIMIT ?"
            params.append(int(max(1, limit)))
            rows = conn.execute(sql, tuple(params)).fetchall()
            return [self._row(r) for r in rows]

    def _cascade_delete_refs(self, fact_id: str) -> None:
        """Audit R3 #16: a hard fact-delete must cascade to its references so no
        dangling rows survive — unresolved contradictions citing a now-deleted id
        (which poison the surviving partner to 'contested' forever, R2 #10) and
        entity_facts links (which leave PPR/anchor recall pointing at dead ids).
        Fail-soft: a missing/locked side-store never blocks the delete."""
        try:
            from .contradiction import ContradictionStore
            ContradictionStore(self.db_path).resolve_all_for_fact(
                fact_id, note="partner fact deleted")
        except Exception:  # noqa: BLE001 — refs cleanup must never break delete
            pass
        try:
            import sqlite3

            from .entity_populate import entity_kg_path_for
            kg = entity_kg_path_for(self.db_path)
            if kg.exists():
                with sqlite3.connect(str(kg)) as c:
                    c.execute(
                        "DELETE FROM entity_facts WHERE fact_id = ?", (fact_id,))
        except Exception:  # noqa: BLE001
            pass

    @staticmethod
    def _relink_through(conn, fact_id: str) -> None:
        """Re-link incoming supersession pointers THROUGH a row about to be
        deleted (review 5-lenti C4): rows pointing at ``fact_id`` inherit its
        successor, so A -> B(deleted) -> C stays walkable as A -> C and a later
        ``purge_history`` closes over the whole chain in both directions.
        Without this the plain delete digs a dangling hole: purge(A) never
        reaches C (stays LIVE), purge(C) never reaches A (resurrectable via
        as_of). No successor -> pointers left as-is (behaviour unchanged;
        NULLing them would resurrect retired versions into the live set)."""
        row = conn.execute(
            "SELECT superseded_by FROM facts WHERE id = ?", (fact_id,),
        ).fetchone()
        succ = row[0] if row else None
        if succ and succ != fact_id:
            conn.execute(
                "UPDATE facts SET superseded_by = ? WHERE superseded_by = ?",
                (succ, fact_id))

    def delete(self, fact_id: str) -> bool:
        """FORGIA pezzo #202: delete one fact by id (privacy / GDPR).

        Returns True iff a row was actually removed.
        """
        with self._connect() as conn:
            self._relink_through(conn, fact_id)
            cur = conn.execute(
                "DELETE FROM facts WHERE id = ?", (fact_id,),
            )
            removed = cur.rowcount > 0
        # Cycle #135: invalidate the recall cache on delete.
        if removed:
            self._cache_version += 1
            self._cascade_delete_refs(fact_id)
        return removed

    def delete_with_undo(self, fact_id: str) -> dict[str, Any]:
        """Cycle 2026-05-27 round 13 P0c — delete + emit undo handle.

        Wraps ``delete()`` with a pre-op snapshot in facts_undo_log.
        Returns ``{ok, fact_id, removed, op_id}`` where op_id is the
        handle to pass to ``undo_op(op_id)`` for restoration.

        If the fact does not exist, removed=False and op_id=None — no
        undo handle is created (no row to restore).
        """
        from .undo_log import snapshot_pre_op
        with self._connect() as conn:
            op_id = snapshot_pre_op(conn, "forget", fact_id)
            if op_id is None:
                # Fact didn't exist; nothing to delete or undo.
                return {
                    "ok": True, "fact_id": fact_id,
                    "removed": False, "op_id": None,
                }
            self._relink_through(conn, fact_id)   # C4: keep chains walkable
            cur = conn.execute(
                "DELETE FROM facts WHERE id = ?", (fact_id,),
            )
            removed = cur.rowcount > 0
        if removed:
            self._cache_version += 1
            self._cascade_delete_refs(fact_id)
        return {
            "ok": True, "fact_id": fact_id,
            "removed": removed, "op_id": op_id,
        }

    def undo_destructive_op(self, op_id: str) -> dict[str, Any]:
        """Undo a previous delete_with_undo / supersede_with_undo.

        Returns the dict from undo_log.undo_op. On successful restore,
        invalidates the recall cache so the restored fact reappears in
        the next recall call.
        """
        from .undo_log import undo_op
        with self._connect() as conn:
            result = undo_op(conn, op_id)
        if result.get("ok"):
            self._cache_version += 1
        return result

    def list_undoable_ops(self, *, limit: int = 20) -> list[dict[str, Any]]:
        """List the N most recent undoable ops (not yet undone, not expired)."""
        from .undo_log import list_undoable
        with self._connect() as conn:
            entries = list_undoable(conn, limit=limit)
        return [
            {
                "op_id": e.op_id, "op_type": e.op_type,
                "fact_id": e.fact_id, "created_at": e.created_at,
                "ttl_expires_at": e.ttl_expires_at,
            }
            for e in entries
        ]

    def quarantine_fact(self, fact_id: str, *, reason: str = "") -> bool:
        """Flip a fact to ``status='quarantined'`` — used by the Tier-2 consolidation
        triage (assess_claim_trust → declass) to withhold a coincidental/ephemeral claim
        from the default recall view WITHOUT deleting it (reversible: the row stays for
        audit/lineage and can be restored by deterministic evidence). Mirrors
        :meth:`mark_orphaned`. Returns True iff a row existed and changed; idempotent
        no-op (False) when already quarantined or unknown. Never raises."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT status FROM facts WHERE id = ?", (fact_id,),
            ).fetchone()
            if row is None:
                return False
            current_status = row["status"] or "model_claim"
            if current_status == "quarantined":
                return False
            conn.execute(
                "UPDATE facts SET status = 'quarantined' WHERE id = ?", (fact_id,),
            )
        self._cache_version += 1  # visibility change → rebuild cached corpus next recall
        try:
            from .observability import emit as _emit
            _emit("fact_quarantined", fact_id=fact_id, reason=(reason or "")[:200],
                  prior_status=current_status)
        except Exception:  # noqa: BLE001 — observability never breaks mutator
            pass
        return True

    def restore_fact(self, fact_id: str, *, to_status: str = "model_claim",
                     reason: str = "") -> bool:
        """Un-quarantine: flip a ``quarantined`` fact back to ``to_status`` (the reverse of
        :meth:`quarantine_fact`) — makes the Tier-2 triage genuinely REVERSIBLE (a wrongly-
        declassed fact, or one corroborated by later evidence, returns to the live view).
        Returns True iff a quarantined row existed and was restored; False otherwise (only
        quarantined rows are restorable — never silently un-orphans/un-supersedes). Never raises."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT status FROM facts WHERE id = ?", (fact_id,),
            ).fetchone()
            if row is None or (row["status"] or "") != "quarantined":
                return False
            conn.execute(
                "UPDATE facts SET status = ? WHERE id = ?", (to_status, fact_id),
            )
        self._cache_version += 1  # back into the live view → rebuild cache next recall
        try:
            from .observability import emit as _emit
            _emit("fact_restored", fact_id=fact_id, to_status=to_status,
                  reason=(reason or "")[:200])
        except Exception:  # noqa: BLE001
            pass
        return True

    def mark_orphaned(self, fact_id: str, *, reason: str = "") -> bool:
        """Cycle #137 — L2 mutation: flip a fact to ``status='orphaned'``.

        Used by the anti-confabulation reconciler (cycle 132 detection +
        cycle 133 MCP tool) to scrub facts that would fail an L1/L1.5/L1.7
        check today. The row stays in the DB for lineage/audit but
        disappears from the default-filter recall view.

        Args:
            fact_id: the id of the fact to mark.
            reason: optional human-readable reason. Stored as a note in
                the audit log via observability.emit; the fact row
                itself only carries the status flip.

        Returns:
            True iff a row existed and was actually updated. False when
            the id is unknown OR when the row is already orphaned
            (idempotent no-op). Never raises.
        """
        with self._connect() as conn:
            row = conn.execute(
                "SELECT status FROM facts WHERE id = ?", (fact_id,),
            ).fetchone()
            if row is None:
                return False
            current_status = row["status"] or "model_claim"
            if current_status == "orphaned":
                # Idempotent: already orphaned, nothing to do.
                return False
            conn.execute(
                "UPDATE facts SET status = 'orphaned' WHERE id = ?",
                (fact_id,),
            )
        # Cycle #135.A invariant: any default-filter visibility change
        # must bump the cache version. Orphaned rows leave the live view,
        # so the next recall() must rebuild the cached corpus.
        self._cache_version += 1
        # Best-effort observability hook (cycle #134 BUS pattern). No
        # subprocess — pure in-process emit.
        try:
            from .observability import emit as _emit
            _emit(
                "fact_orphaned",
                fact_id=fact_id,
                reason=(reason or "")[:200],
                prior_status=current_status,
            )
        except Exception:  # noqa: BLE001 — observability never breaks mutator
            pass
        return True

    def count(self, *, include_superseded: bool = False) -> int:
        with self._connect() as conn:
            if include_superseded:
                return conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
            return conn.execute(
                "SELECT COUNT(*) FROM facts WHERE superseded_by IS NULL"
            ).fetchone()[0]

    def count_superseded(self) -> int:
        """Cycle #78: count facts marked as superseded."""
        with self._connect() as conn:
            return conn.execute(
                "SELECT COUNT(*) FROM facts WHERE superseded_by IS NOT NULL"
            ).fetchone()[0]

    def supersede(self, old_id: str, new_id: str, *, reason: str = "") -> dict[str, Any]:
        """Cycle #78 — declare ``old_id`` superseded by ``new_id``.

        Args:
            old_id: fact id of the obsolete claim. Stays in DB for lineage.
            new_id: fact id that REPLACES the old claim. Must exist.
            reason: human-readable why this supersession happened.

        Returns:
            dict ``{ok, old_id, new_id, reason, superseded_at,
            idempotent_noop}``. ``idempotent_noop=True`` when the same
            (old, new) pair was already declared with the same reason.

        Raises:
            SupersedeError: old==new, or either id missing in DB.
            SupersedeConflict: old_id was already superseded by a
                DIFFERENT new_id. Caller chooses chain vs reassign.
        """
        if old_id == new_id:
            raise SupersedeError("cannot supersede a fact with itself (self-supersede)")
        with self._connect() as conn:
            old_row = conn.execute(
                "SELECT superseded_by, superseded_reason FROM facts WHERE id = ?",
                (old_id,),
            ).fetchone()
            if old_row is None:
                raise SupersedeError(f"old_id {old_id!r} not found in facts table")
            new_row = conn.execute(
                "SELECT 1 FROM facts WHERE id = ?", (new_id,),
            ).fetchone()
            if new_row is None:
                raise SupersedeError(f"new_id {new_id!r} not found in facts table")

            existing_super = old_row["superseded_by"]
            existing_reason = old_row["superseded_reason"]
            now = time.time()
            if existing_super == new_id:
                # Already superseded by the same new_id.
                if existing_reason == reason:
                    return {
                        "ok": True, "old_id": old_id, "new_id": new_id,
                        "reason": reason, "superseded_at": now,
                        "idempotent_noop": True,
                    }
                # Same pair, different reason → update reason ONLY, keep ts.
                conn.execute(
                    "UPDATE facts SET superseded_reason = ? WHERE id = ?",
                    (reason, old_id),
                )
                # Cycle #135.A (critic counterexample fix 2026-05-17):
                # any DB mutation on the facts table must invalidate the
                # recall cache, otherwise a stale snapshot may still
                # surface the row as live.
                self._cache_version += 1
                return {
                    "ok": True, "old_id": old_id, "new_id": new_id,
                    "reason": reason, "superseded_at": now,
                    "idempotent_noop": False,
                }
            if existing_super is not None and existing_super != new_id:
                raise SupersedeConflict(
                    f"fact {old_id!r} already superseded by {existing_super!r}; "
                    f"refusing to reassign to {new_id!r}. Declare an "
                    f"explicit chain ({existing_super}→{new_id}) instead."
                )

            # G5 property counterexample (hypothesis 2026-07-04, [(A,B),(B,A)]):
            # if new_id's own supersession chain already reaches old_id,
            # declaring old→new closes a CYCLE — every superseded_by walker
            # (supersede_chain, lineage trace, "latest live version") would
            # loop, and no fact in the ring stays live. Reject like reassign.
            # NO hop cap: the 2026-07-04 adversarial review closed a 70-ring
            # through the earlier `hops <= 64` escape (all 70 facts silently
            # vanished from default recall). The walk always terminates: the
            # seen-set breaks on pre-existing corruption, else it ends at a
            # live head (superseded_by IS NULL). Known limit: two concurrent
            # writers closing a ring from opposite sides can both pass this
            # read-check (snapshot reads; the A5 compare-and-set only guards
            # the SAME row) — accepted and documented, same trade as A5.
            chain_cur, seen_walk = new_id, set()
            while chain_cur is not None and chain_cur not in seen_walk:
                if chain_cur == old_id:
                    raise SupersedeError(
                        f"supersede({old_id!r} → {new_id!r}) would create a "
                        f"supersession cycle (chain from {new_id!r} reaches "
                        f"{old_id!r})"
                    )
                seen_walk.add(chain_cur)
                nxt = conn.execute(
                    "SELECT superseded_by FROM facts WHERE id = ?",
                    (chain_cur,),
                ).fetchone()
                chain_cur = nxt["superseded_by"] if nxt else None

            cur = conn.execute(
                "UPDATE facts SET superseded_by = ?, superseded_at = ?, "
                "superseded_reason = ? WHERE id = ? AND superseded_by IS NULL",
                (new_id, now, reason, old_id),
            )
            if cur.rowcount == 0:
                # A5 (audit 2026-06-08): lost a concurrent race — another writer
                # set superseded_by between our SELECT above and this UPDATE. The
                # old UNCONDITIONAL update silently overwrote it (last-writer-wins
                # → one supersession lineage lost, the conflict guard defeated).
                # The compare-and-set above is atomic; re-read the winner and
                # surface it consistently with the sequential guard.
                won_row = conn.execute(
                    "SELECT superseded_by FROM facts WHERE id = ?", (old_id,),
                ).fetchone()
                won = won_row["superseded_by"] if won_row else None
                if won == new_id:
                    return {
                        "ok": True, "old_id": old_id, "new_id": new_id,
                        "reason": reason, "superseded_at": now,
                        "idempotent_noop": True,
                    }
                raise SupersedeConflict(
                    f"fact {old_id!r} was concurrently superseded by {won!r}; "
                    f"refusing to reassign to {new_id!r}."
                )
        # Cycle #135.A (critic counterexample fix): the row that was
        # live up to this call is now hidden behind the default-filter
        # ``WHERE superseded_by IS NULL``. Bump the recall-cache version
        # so the next recall() rebuilds the matrix without ``old_id``.
        self._cache_version += 1
        return {
            "ok": True, "old_id": old_id, "new_id": new_id,
            "reason": reason, "superseded_at": now,
            "idempotent_noop": False,
        }

    def auto_supersede_on_contradiction(
        self,
        new_id: str,
        contradicting_ids: Iterable[str],
        *,
        reason: str = "",
    ) -> dict[str, Any]:
        """Auto-invalidate (supersede, NOT delete) older facts that a NEWER,
        higher-trust fact contradicts.

        This is the wiring target for the anti-confab gate's L3 signal:
        ``run_validation_gate`` already returns ``contradicting_fact_ids`` but
        never acts on them, so a claim proven wrong by later evidence stays
        ``live`` in recall forever (root cause of "memory keeps wrong info").
        Reuses :meth:`supersede`, so the old rows remain in the DB for lineage
        and merely drop out of the default recall filter
        (``WHERE superseded_by IS NULL``).

        Safety rule (NON-NEGOTIABLE): a fact is superseded ONLY when the new
        fact's trust rank (``_STATUS_RANK``) is STRICTLY GREATER than the old
        fact's. A weak/unverified claim can never invalidate a stronger one —
        this prevents a fresh ``model_claim`` from wiping a ``verified`` fact.

        Args:
            new_id: id of the freshly-written fact that triggered detection.
            contradicting_ids: candidate older fact ids (gate / contradiction
                scan output).
            reason: optional human note; a default is synthesised when empty.

        Returns:
            ``{"superseded": [...], "skipped": [...], "missing": [...]}``.
              - superseded: ids marked ``superseded_by=new_id``.
              - skipped: present but NOT superseded (equal/higher trust, already
                superseded, self-reference, or a supersede conflict).
              - missing: ids (incl. ``new_id`` if absent) not found in the DB.
        """
        result: dict[str, Any] = {"superseded": [], "skipped": [], "missing": []}
        new_fact = self.get(new_id)
        if new_fact is None:
            result["missing"].append(new_id)
            return result
        # FIX 2026-06-09 (audit#3-r3 R10): a SUPERSEDED (obsolete) fact must
        # never become a supersession target — it would invalidate live facts
        # using a status rank that is itself stale. Skip the whole batch.
        if new_fact.superseded_by:
            result["skipped"] = [oid for oid in contradicting_ids if oid]
            return result
        new_rank = _STATUS_RANK.get(new_fact.status, 0)
        seen: set[str] = set()
        for old_id in contradicting_ids:
            if not old_id or old_id == new_id or old_id in seen:
                continue
            seen.add(old_id)
            old_fact = self.get(old_id)
            if old_fact is None:
                result["missing"].append(old_id)
                continue
            if old_fact.superseded_by:
                result["skipped"].append(old_id)
                continue
            old_rank = _STATUS_RANK.get(old_fact.status, 0)
            if new_rank <= old_rank:
                # Safety: never let a weaker/equal claim invalidate a stronger one.
                result["skipped"].append(old_id)
                continue
            note = reason or (
                f"auto-supersede: contradicted by newer higher-trust fact "
                f"{new_id} (status={new_fact.status})"
            )
            try:
                self.supersede(old_id, new_id, reason=note)
                result["superseded"].append(old_id)
            except (SupersedeError, SupersedeConflict):
                result["skipped"].append(old_id)
        return result

    def direct_predecessors(self, fact_id: str, *, limit: int = 10) -> list[Fact]:
        """Facts this fact directly REPLACED (``superseded_by == fact_id``),
        most recently retired first. The inverse edge of
        :meth:`get_supersession_chain` (which walks forward to the live
        successor); uses ``idx_facts_superseded_by``. Raw material for
        answer-with-history: "changed from X to Y on <date>"."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id FROM facts WHERE superseded_by = ? "
                "ORDER BY COALESCE(superseded_at, 0) DESC, created_at DESC "
                "LIMIT ?",
                (fact_id, int(limit))).fetchall()
        out: list[Fact] = []
        for r in rows:
            f = self.get(r["id"])
            if f is not None:
                out.append(f)
        return out

    def get_supersession_chain(self, fact_id: str) -> list[Fact]:
        """Walk forward from ``fact_id`` along ``superseded_by`` pointers
        until a terminal (live) fact is reached or a cycle is detected.

        Returns:
            list[Fact] starting with the fact at ``fact_id`` and ending
            with the current live successor. Singleton when the fact is
            not superseded. Empty when ``fact_id`` does not exist.

        Cycle protection: a chain longer than 1000 hops is truncated
        with no error — defensive against pathological data only;
        real chains should be ≤ 5.
        """
        chain: list[Fact] = []
        seen: set[str] = set()
        cursor = fact_id
        for _ in range(1000):
            if cursor in seen:
                break
            seen.add(cursor)
            f = self.get(cursor)
            if f is None:
                break
            chain.append(f)
            if f.superseded_by is None:
                break
            cursor = f.superseded_by
        return chain

    def supersede_chain(
        self, ids: list[str], *, reason: str = "",
        atomic: bool = True,
    ) -> dict[str, Any]:
        """Cycle #81 (2026-05-16) — declare a multi-hop supersession
        chain ``ids[0]→ids[1]→...→ids[-1]`` in one call.

        Args:
            ids: ordered list of fact ids (oldest → newest). Length >= 2.
            reason: applied uniformly to every hop.
            atomic: when True (default), any error mid-chain rolls back
                the previously-applied hops (state unchanged). When
                False, applies what it can and returns per-hop status.

        Returns:
            dict with keys: ``ok``, ``n_applied``, ``n_idempotent``,
            ``n_skipped``, ``chain``, ``hops``, ``error``. Status per
            hop: ``applied``, ``idempotent``, ``conflict``, ``invalid``,
            ``rolled_back``.

        Raises:
            SupersedeError: structural input invalid (len < 2 or any
                consecutive pair has the same id, i.e. self-loop in
                the chain).
        """
        if not ids or len(ids) < 2:
            raise SupersedeError(
                "supersede_chain requires at least 2 ids (old → new)"
            )
        # Detect self-loops (consecutive duplicates) BEFORE touching DB.
        for i in range(len(ids) - 1):
            if ids[i] == ids[i + 1]:
                raise SupersedeError(
                    f"self-loop in chain at index {i}: ids[{i}] == ids[{i+1}]"
                )

        hops: list[dict[str, Any]] = []
        # Cycle #81b critic-fix (job cc004125dbaff256 split 1-1-0 conf 0.85):
        # rollback log = (old_id, pre_super, pre_at, pre_reason). A pure
        # idempotent_noop=True from supersede() means NO row mutation, so
        # skip rollback log. A reason-update (same pair, different reason)
        # IS a mutation that must be reversed.
        rollback_log: list[tuple[str, str | None, float | None, str | None]] = []
        n_applied = 0
        n_idem = 0
        n_skipped = 0
        error: str | None = None

        for i in range(len(ids) - 1):
            old_id, new_id = ids[i], ids[i + 1]
            try:
                pre = self.get(old_id)
            except Exception:
                pre = None
            pre_super = pre.superseded_by if pre is not None else None
            pre_at = pre.superseded_at if pre is not None else None
            pre_reason = pre.superseded_reason if pre is not None else None
            try:
                result = self.supersede(old_id, new_id, reason=reason)
                already_pointing = (pre_super == new_id)
                pure_noop = bool(result.get("idempotent_noop"))
                if pure_noop:
                    n_idem += 1
                    hops.append({
                        "old": old_id, "new": new_id, "status": "idempotent",
                    })
                elif already_pointing:
                    # Reason-update: not a structurally new hop, but row
                    # WAS mutated → must be reversible on rollback.
                    n_idem += 1
                    rollback_log.append(
                        (old_id, pre_super, pre_at, pre_reason)
                    )
                    hops.append({
                        "old": old_id, "new": new_id, "status": "idempotent",
                    })
                else:
                    n_applied += 1
                    rollback_log.append(
                        (old_id, pre_super, pre_at, pre_reason)
                    )
                    hops.append({
                        "old": old_id, "new": new_id, "status": "applied",
                    })
            except SupersedeConflict as exc:
                error = f"hop {i} conflict: {exc}"
                hops.append({
                    "old": old_id, "new": new_id, "status": "conflict",
                    "reason": str(exc),
                })
                if atomic:
                    self._restore_supersession_snapshots(rollback_log)
                    for h in hops:
                        if h["status"] == "applied":
                            h["status"] = "rolled_back"
                    return {
                        "ok": False, "n_applied": 0, "n_idempotent": n_idem,
                        "n_skipped": 1, "chain": list(ids),
                        "hops": hops, "error": error,
                    }
                else:
                    n_skipped += 1
                    continue
            except SupersedeError as exc:
                error = f"hop {i} invalid: {exc}"
                hops.append({
                    "old": old_id, "new": new_id, "status": "invalid",
                    "reason": str(exc),
                })
                if atomic:
                    self._restore_supersession_snapshots(rollback_log)
                    for h in hops:
                        if h["status"] == "applied":
                            h["status"] = "rolled_back"
                    return {
                        "ok": False, "n_applied": 0, "n_idempotent": n_idem,
                        "n_skipped": 1, "chain": list(ids),
                        "hops": hops, "error": error,
                    }
                else:
                    n_skipped += 1
                    continue
            except Exception as exc:  # noqa: BLE001
                # A-4/A9 (audit#2 2026-06-08): the docstring promises atomic
                # all-or-nothing on ANY mid-chain error, but only the two
                # supersede-specific exceptions were caught. An unexpected error
                # (sqlite 'database is locked', a coherence-hook bug, ...) used
                # to escape WITHOUT rolling back the already-applied hops. Honor
                # the contract: in atomic mode restore snapshots and report
                # ok=False; the error is surfaced in the return, never swallowed.
                error = f"hop {i} unexpected error: {exc}"
                hops.append({
                    "old": old_id, "new": new_id, "status": "error",
                    "reason": str(exc),
                })
                if atomic:
                    self._restore_supersession_snapshots(rollback_log)
                    for h in hops:
                        if h["status"] == "applied":
                            h["status"] = "rolled_back"
                    return {
                        "ok": False, "n_applied": 0, "n_idempotent": n_idem,
                        "n_skipped": 1, "chain": list(ids),
                        "hops": hops, "error": error,
                    }
                else:
                    n_skipped += 1
                    continue

        return {
            "ok": error is None,
            "n_applied": n_applied,
            "n_idempotent": n_idem,
            "n_skipped": n_skipped,
            "chain": list(ids),
            "hops": hops,
            "error": error,
        }

    def _restore_supersession_snapshots(
        self,
        snapshots: list[tuple[str, str | None, float | None, str | None]],
    ) -> None:
        """Cycle #81b atomic rollback helper. Each snapshot is
        ``(old_id, pre_super, pre_at, pre_reason)``. Restores exact
        pre-state — distinguishes "was unsuperseded" (all None) from
        "was already superseded with original reason" (preserve
        pointer + ts + original reason). No-op on empty.
        """
        if not snapshots:
            return
        with self._connect() as conn:
            for old_id, pre_super, pre_at, pre_reason in snapshots:
                conn.execute(
                    "UPDATE facts SET superseded_by = ?, "
                    "superseded_at = ?, superseded_reason = ? WHERE id = ?",
                    (pre_super, pre_at, pre_reason, old_id),
                )
        # Cycle #135.A (critic counterexample fix): the rollback flips
        # rows back to their pre-supersession state. Each restored row
        # may transition from "hidden" to "live" (or vice-versa) under
        # the default filter — invalidate the recall cache.
        self._cache_version += 1

    def summary_topic(
        self, topic_glob: str, *,
        max_facts: int = 50,
        include_lineage: bool = True,
        include_superseded: bool = False,
    ) -> dict[str, Any]:
        """Cycle #79 (2026-05-16) — narrative aggregator for a topic glob.

        Counts (n_total / n_live / n_superseded), distinct topics_seen,
        capped facts payload (newest-first), union source_episodes
        (lineage_episodes), and forward supersession chains for facts
        matched-and-superseded.

        Glob: ``*`` → SQL ``%``; ``?`` → SQL ``_``. Literal ``%`` / ``_``
        in input are escaped with ``\\`` so they stay literal.

        Args:
            topic_glob: ``project/nexus/*`` or exact topic.
            max_facts: cap on returned ``facts`` (counts unaffected).
            include_lineage: when False, lineage_episodes is empty.
            include_superseded: when True, facts payload includes them.

        Returns:
            dict {topic_glob, n_total, n_live, n_superseded, topics_seen,
                  facts, lineage_episodes, supersession_chains}.
        """
        like_pattern = _glob_to_like(topic_glob)
        with self._connect() as conn:
            n_total = conn.execute(
                "SELECT COUNT(*) FROM facts WHERE topic LIKE ? ESCAPE '\\'",
                (like_pattern,),
            ).fetchone()[0]
            n_super = conn.execute(
                "SELECT COUNT(*) FROM facts WHERE topic LIKE ? ESCAPE '\\' "
                "AND superseded_by IS NOT NULL",
                (like_pattern,),
            ).fetchone()[0]
            n_live = n_total - n_super
            topics_seen = [
                row[0] for row in conn.execute(
                    "SELECT DISTINCT topic FROM facts WHERE topic LIKE ? "
                    "ESCAPE '\\' ORDER BY topic",
                    (like_pattern,),
                ).fetchall()
            ]
            sql = "SELECT * FROM facts WHERE topic LIKE ? ESCAPE '\\'"
            params: list[Any] = [like_pattern]
            if not include_superseded:
                sql += " AND superseded_by IS NULL"
            sql += " ORDER BY created_at DESC LIMIT ?"
            params.append(int(max(1, max_facts)))
            payload_rows = conn.execute(sql, tuple(params)).fetchall()
            facts_payload = [
                self._fact_to_summary_dict(self._row(r)) for r in payload_rows
            ]
            lineage_episodes: list[str] = []
            if include_lineage:
                all_rows = conn.execute(
                    "SELECT source_episodes FROM facts WHERE topic LIKE ? "
                    "ESCAPE '\\'",
                    (like_pattern,),
                ).fetchall()
                seen: set[str] = set()
                for r in all_rows:
                    for ep in (r[0] or "").split(","):
                        ep = ep.strip()
                        if ep and ep not in seen:
                            seen.add(ep)
                            lineage_episodes.append(ep)
            anchored = conn.execute(
                "SELECT id FROM facts WHERE topic LIKE ? ESCAPE '\\' "
                "AND superseded_by IS NOT NULL",
                (like_pattern,),
            ).fetchall()
        chains: list[list[str]] = []
        seen_anchors: set[str] = set()
        for row in anchored:
            anchor = row[0]
            if anchor in seen_anchors:
                continue
            seen_anchors.add(anchor)
            walked = self.get_supersession_chain(anchor)
            chains.append([f.id for f in walked])
        return {
            "topic_glob": topic_glob,
            "n_total": int(n_total),
            "n_live": int(n_live),
            "n_superseded": int(n_super),
            "topics_seen": topics_seen,
            "facts": facts_payload,
            "lineage_episodes": lineage_episodes,
            "supersession_chains": chains,
        }

    @staticmethod
    def _fact_to_summary_dict(fact: Fact) -> dict[str, Any]:
        return {
            "id": fact.id,
            "topic": fact.topic,
            "proposition": fact.proposition,
            "confidence": fact.confidence,
            "created_at": fact.created_at,
            "source_episodes": list(fact.source_episodes),
            "superseded_by": fact.superseded_by,
        }

    def clear(self) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM facts")
        # SCAN-68 FIX 2026-06-02 (NONNA): invalida la recall-cache. Mancava il
        # bump -> recall(topic=None) continuava a servire fatti FANTASMA dalla
        # cache stantia finche un altro store/delete non bumpava la versione.
        self._cache_version += 1

    @staticmethod
    def _row(r: sqlite3.Row) -> Fact:
        """Deserialize a SQLite row into a Fact.

        Defensive on TWO columns sets that may be missing in legacy rows:
          * Cycle #78 supersession (v2): ``superseded_by/at/reason`` —
            pre-v2 rows have no such keys; defaults to None.
          * Cycle #109 provenance (v3): ``verified_by``/``status``/
            ``source_signature`` — pre-v3 rows likewise; defaults to
            empty list / ``"model_claim"`` / None. JSON-decodes
            ``verified_by``; falls back to empty list on bad JSON.
        """
        # Defensive lookup helpers — sqlite3.Row.keys() exists but
        # accessing an unknown key raises IndexError.
        def _opt(key: str) -> Any:
            try:
                return r[key]
            except (IndexError, KeyError):
                return None

        try:
            vb_raw = r["verified_by"]
        except (IndexError, KeyError):
            vb_raw = "[]"
        try:
            verified_by = json.loads(vb_raw or "[]")
            if not isinstance(verified_by, list):
                verified_by = []
        except (ValueError, TypeError):
            verified_by = []
        try:
            status = r["status"] or "model_claim"
        except (IndexError, KeyError):
            status = "model_claim"
        try:
            source_signature = r["source_signature"]
        except (IndexError, KeyError):
            source_signature = None
        # Cycle 160 (2026-05-19) pattern card v5 columns. Defensive on
        # pre-v5 rows that may lack the keys (handled by ``_opt``).
        tk_raw = _opt("trigger_keywords") or ""
        lt_raw = _opt("lineage_to") or ""
        df_raw = _opt("derives_from") or ""
        return Fact(
            id=r["id"], proposition=r["proposition"], topic=r["topic"],
            confidence=r["confidence"],
            source_episodes=[s for s in (r["source_episodes"] or "").split(",") if s],
            created_at=r["created_at"],
            superseded_by=_opt("superseded_by"),
            superseded_at=_opt("superseded_at"),
            superseded_reason=_opt("superseded_reason"),
            verified_by=verified_by,
            status=status,
            source_signature=source_signature,
            trigger_keywords=[s for s in tk_raw.split(",") if s],
            applicable_when=_opt("applicable_when"),
            worked_example=_opt("worked_example"),
            lineage_to=[s for s in lt_raw.split(",") if s],
            # SCAN-68 FIX 2026-06-02 (NONNA): erano OMESSI -> provenance v6 persa
            # nel roundtrip (il gate anti-confab legge fact.writer_role).
            writer_role=_opt("writer_role") or "agent_inference",
            meta_narrative=bool(_opt("meta_narrative")),
            # v8 (2026-06-03) buco #3. Defensive su righe pre-v8 (None ->
            # freshness lo coalesce a created_at).
            last_verified_at=_opt("last_verified_at"),
            # v10 (2026-06-14) valid-time. Defensive su righe pre-v10 (None ->
            # nessuna scadenza). Il recall lo usa per l'hard-expire.
            valid_until=_opt("valid_until"),
            # v11 (2026-06-19) typed logical-derivation edge. Defensive su righe
            # pre-v11 (vuoto -> propagate dormiente). NON e' lineage_to (narrativo).
            derives_from=[s for s in df_raw.split(",") if s],
            # v12 (2026-06-20) write-time grounding score. Defensive on pre-v12 rows
            # (None -> not computed). float when persisted.
            grounding_score=_opt("grounding_score"),
            asserted_at=_opt("asserted_at"),
            # v14 (2026-07-13) epistemic label. Defensive on pre-v14 rows and on
            # garbage (parse is fail-open -> None = unlabeled).
            epistemic=_epistemic.parse(_opt("epistemic")),
            confidence_tier=_opt("confidence_tier"),
        )
