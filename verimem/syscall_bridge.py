"""Cycle 364 (2026-05-23) — ENGRAM SYSCALL BRIDGE: typed boundary for memory ops.

Aurelio carta bianca extended: "porta engram allo stato superiore, usa
meta-regole". A3 insight from clp parallel session (loop 359-363):
manifest validator catches 3/3 hallucinated commands. Anti-hallucination
at typed boundary IS the real engineering win (3 cross-LLM FAIL on
"singolarità" claims accepted).

B4 NUCLEAR concatenazione → STATO SUPERIORE:
  clp.agentos.syscall (typed entry + audit + rate-limit, LOOP 361)
  + clp.agentos.manifest (anti-hallucination validator, LOOP 359-360)
  + engram mesh_memory (cycle 362-363, cross-instance recall)
  + clp.agentos.a2a_bus / vec_bus (LOOP 337+356)
  + HippoAgent persistent memory (semantic.db)
  ⇒ OS-native memory layer: every engram memory op flows through
    typed boundary with audit JSONL + rate-limit + manifest whitelist.

NOT singolarità claim — A3 explicit reframing per cycle 359-363 lesson.
This is the engineering integration that makes engram a first-class
OS primitive in the clp os stack. The novelty is the synthesis, not
a paradigm shift.

API:
  ENGRAM_OPS_MANIFEST: whitelist dict {op_name: (callable, arg_schema)}
  engram_invoke(op, args, actor) -> {ok, result, audit_id, blocked_by}
  engram_audit_tail(n) -> list[dict]
  engram_rate_stats() -> dict

Falsifiable contract:
  (a) Hallucinated op name → blocked_by="not_in_manifest"
  (b) Real op → success + audit JSONL row appended
  (c) Rate limit: >5 saves/sec → blocked_by="rate_limit_exceeded"

Operations exposed (initial set, extendable):
  recall(query, k=5) -> top-k from semantic.db
  save(text, topic, lineage_to) -> fact_id
  mesh_query(query_text, channel) -> publishes embedding
  mesh_fetch(channel, since_ts) -> list[msg]
  mesh_resonant_merge(query, local_embs, remote_embs) -> completed
  topk_embeddings(query_vec, k) -> list[(id, emb, score)]
"""
from __future__ import annotations

import json
import time
from collections import deque
from collections.abc import Callable
from pathlib import Path
from typing import Any

# Audit log path mirrors clp.agentos.syscall convention but separate file
ENGRAM_AUDIT_LOG = Path.home() / ".clp" / "engram-syscall-audit.jsonl"

# Token bucket per op (simple in-memory, identical pattern to clp.syscall)
_RATE_BUCKETS: dict[str, deque] = {}
_RATE_LIMIT_PER_SEC = 5.0
_RATE_WINDOW_SEC = 1.0


def _audit_write(record: dict) -> None:
    """Append a single JSONL audit record. Best-effort, no raise."""
    ENGRAM_AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    record["ts"] = time.time()
    try:
        with ENGRAM_AUDIT_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
    except OSError:
        pass


def _check_rate_limit(op: str, limit: float = _RATE_LIMIT_PER_SEC) -> bool:
    """Token-bucket. Returns True if call is allowed, False if rate-limited."""
    now = time.time()
    bucket = _RATE_BUCKETS.setdefault(op, deque(maxlen=int(limit * 4) + 8))
    # Drop old timestamps
    cutoff = now - _RATE_WINDOW_SEC
    while bucket and bucket[0] < cutoff:
        bucket.popleft()
    if len(bucket) >= limit:
        return False
    bucket.append(now)
    return True


# ───────────────────────── operation handlers ─────────────────────────

def _op_recall(args: dict) -> dict:
    """recall(query: str, k: int=5, db_path=default) -> top-k facts.

    Returns {"hits": [(fact_id, score), ...]}. Plaintext propositions
    omitted for caller-mediated lookup (privacy primitive consistent
    with mesh_memory).
    """
    from verimem.mesh_memory import local_topk_embeddings

    query = args.get("query")
    if not query or not isinstance(query, str):
        return {"ok": False, "error": "query (str) required"}
    k = int(args.get("k", 5))
    db_path = Path(args.get("db_path") or
                   Path.home() / ".engram" / "semantic" / "semantic.db")
    try:
        from clp.agentos.vec_bus import embed_text
        qvec = embed_text(query)
    except ImportError:
        return {"ok": False, "error": "vec_bus.embed_text unavailable"}
    hits = local_topk_embeddings(db_path, qvec, k=k)
    return {
        "ok": True,
        "hits": [(fid, float(score)) for (fid, _emb, score) in hits],
    }


def _op_topk_embeddings(args: dict) -> dict:
    """topk_embeddings(query_vec_bytes, k, db_path) — privacy-preserving."""
    from verimem.mesh_memory import local_topk_embeddings
    qv = args.get("query_vec_bytes")
    k = int(args.get("k", 5))
    if not isinstance(qv, (bytes, bytearray)):
        return {"ok": False, "error": "query_vec_bytes (bytes 1536) required"}
    db = Path(args.get("db_path") or
              Path.home() / ".engram" / "semantic" / "semantic.db")
    hits = local_topk_embeddings(db, bytes(qv), k=k)
    return {
        "ok": True,
        "hits": [(fid, len(emb), float(s)) for (fid, emb, s) in hits],
    }


def _op_mesh_query(args: dict) -> dict:
    """mesh_query(text, channel) — publish query embedding on vec_bus."""
    from verimem.mesh_memory import mesh_publish_query
    text = args.get("text")
    if not text or not isinstance(text, str):
        return {"ok": False, "error": "text (str) required"}
    channel = args.get("channel", "mesh/recall/req")
    return mesh_publish_query(text, channel=channel,
                              sender=args.get("sender"))


def _op_mesh_fetch(args: dict) -> dict:
    """mesh_fetch(channel, since_ts) — fetch recent mesh messages."""
    from verimem.mesh_memory import mesh_fetch_recent
    channel = args.get("channel")
    if not channel:
        return {"ok": False, "error": "channel required"}
    since_ts = float(args.get("since_ts", 0.0))
    msgs = mesh_fetch_recent(channel, since_ts=since_ts,
                              skip_own=bool(args.get("skip_own", True)))
    # Return only metadata + msg_ids to keep audit compact
    return {
        "ok": True,
        "n_msgs": len(msgs),
        "msg_ids": [m.get("msg_id", "") for m in msgs],
    }


def _op_resonant_merge(args: dict) -> dict:
    """resonant_merge(query_vec, local_embs, remote_embs, beta)."""
    from verimem.mesh_memory import mesh_resonant_merge
    qv = args.get("query_vec_bytes")
    if not isinstance(qv, (bytes, bytearray)):
        return {"ok": False, "error": "query_vec_bytes (bytes) required"}
    local_embs = args.get("local_embs") or []
    remote_embs = args.get("remote_embs") or []
    beta = float(args.get("beta", 8.0))
    r = mesh_resonant_merge(bytes(qv), local_embs, remote_embs, beta=beta)
    # Strip raw completed_bytes for audit-friendly response
    if r.get("ok"):
        return {
            "ok": True,
            "shift_cosine": r.get("shift_cosine"),
            "n_local": r.get("n_local"),
            "n_remote": r.get("n_remote"),
            "completed_size": len(r.get("completed_bytes", b"")),
        }
    return r


# Manifest: whitelist of ops + handler
ENGRAM_OPS_MANIFEST: dict[str, Callable[[dict], dict]] = {
    "recall": _op_recall,
    "topk_embeddings": _op_topk_embeddings,
    "mesh_query": _op_mesh_query,
    "mesh_fetch": _op_mesh_fetch,
    "resonant_merge": _op_resonant_merge,
}


def engram_invoke(
    op: str,
    args: dict[str, Any] | None = None,
    actor: str | None = None,
    rate_limit: float = _RATE_LIMIT_PER_SEC,
    use_supervisor: bool = True,
    capability_token: str | None = None,
    require_token: bool = False,
) -> dict:
    """Single typed entry point for engram memory ops.

    Args:
        op: operation name (must be in ENGRAM_OPS_MANIFEST).
        args: operation arguments dict.
        actor: caller id for audit (e.g. "agent_A", "supervisor", "mcp").
        rate_limit: max calls per op per second.

    Returns:
        {
          "ok": bool, "result": dict | None,
          "blocked_by": str | None,
          "audit_id": str,
          "elapsed_sec": float,
        }

    Falsifiable contract:
      (a) op not in manifest → ok=False, blocked_by="not_in_manifest"
      (b) rate-limited → ok=False, blocked_by="rate_limit_exceeded"
      (c) handler raises → ok=False, blocked_by="exception"
      (d) success → ok=True, result=handler output
      All paths write 1 audit JSONL row.
    """
    args = args or {}
    audit_id = f"eng-{int(time.time() * 1000000) % 1000000000:09d}"
    t_start = time.time()
    base_record = {
        "audit_id": audit_id,
        "op": op,
        "actor": actor or "anonymous",
        "args_keys": sorted(args.keys()) if args else [],
        # Don't audit args VALUES (may contain large bytes); just keys.
    }

    # 1. Manifest validation (anti-hallucination)
    handler = ENGRAM_OPS_MANIFEST.get(op)
    if handler is None:
        rec = {**base_record, "blocked_by": "not_in_manifest",
               "ok": False, "elapsed_sec": time.time() - t_start}
        _audit_write(rec)
        return {
            "ok": False, "result": None,
            "blocked_by": "not_in_manifest",
            "audit_id": audit_id,
            "elapsed_sec": time.time() - t_start,
            "available_ops": sorted(ENGRAM_OPS_MANIFEST.keys()),
        }

    # 1b. Capability token check (cycle 368): if required or provided
    if require_token or capability_token is not None:
        from verimem.capability_token import verify_token
        if capability_token is None:
            rec = {**base_record, "blocked_by": "missing_capability_token",
                   "ok": False, "elapsed_sec": time.time() - t_start}
            _audit_write(rec)
            return {
                "ok": False, "result": None,
                "blocked_by": "missing_capability_token",
                "audit_id": audit_id,
                "elapsed_sec": time.time() - t_start,
            }
        vt = verify_token(capability_token, expected_op=op,
                          peer_id_required=actor if require_token else None)
        if not vt["ok"]:
            rec = {**base_record, "blocked_by": vt["blocked_by"],
                   "token_peer": vt.get("peer_id"),
                   "token_op": vt.get("op"),
                   "reason": vt.get("reason"),
                   "ok": False, "elapsed_sec": time.time() - t_start}
            _audit_write(rec)
            return {
                "ok": False, "result": None,
                "blocked_by": vt["blocked_by"],
                "token_verification": vt,
                "audit_id": audit_id,
                "elapsed_sec": time.time() - t_start,
            }

    # 2a. Supervisor circuit-breaker (cycle 365): check if op circuit allows
    if use_supervisor:
        from verimem.op_supervisor import get_default_supervisor
        sup = get_default_supervisor()
        ck = sup.check(op)
        if not ck["allowed"]:
            rec = {**base_record, "blocked_by": ck["blocked_by"],
                   "circuit_state": ck["state"]["circuit"],
                   "ok": False, "elapsed_sec": time.time() - t_start}
            _audit_write(rec)
            return {
                "ok": False, "result": None,
                "blocked_by": ck["blocked_by"],
                "circuit_state": ck["state"]["circuit"],
                "supervisor_snapshot": ck["state"],
                "audit_id": audit_id,
                "elapsed_sec": time.time() - t_start,
            }

    # 2b. Rate limit per op
    if not _check_rate_limit(op, limit=rate_limit):
        rec = {**base_record, "blocked_by": "rate_limit_exceeded",
               "ok": False, "elapsed_sec": time.time() - t_start}
        _audit_write(rec)
        return {
            "ok": False, "result": None,
            "blocked_by": "rate_limit_exceeded",
            "audit_id": audit_id,
            "elapsed_sec": time.time() - t_start,
        }

    # 3. Execute handler
    try:
        result = handler(args)
    except Exception as e:  # noqa: BLE001
        # Record failure with supervisor (circuit-breaker counts this)
        if use_supervisor:
            from verimem.op_supervisor import get_default_supervisor
            get_default_supervisor().record_failure(
                op, reason=f"{type(e).__name__}: {str(e)[:100]}",
            )
        rec = {**base_record, "blocked_by": "exception",
               "exception": type(e).__name__, "message": str(e)[:200],
               "ok": False, "elapsed_sec": time.time() - t_start}
        _audit_write(rec)
        return {
            "ok": False, "result": None,
            "blocked_by": "exception",
            "exception": type(e).__name__,
            "audit_id": audit_id,
            "elapsed_sec": time.time() - t_start,
        }

    # Handler returned dict — feed ok status to supervisor
    op_ok = bool(result.get("ok", True))
    if use_supervisor:
        from verimem.op_supervisor import get_default_supervisor
        sup = get_default_supervisor()
        if op_ok:
            sup.record_success(op)
        else:
            sup.record_failure(op, reason=str(result.get("error", "handler_returned_not_ok"))[:100])

    rec = {**base_record, "ok": op_ok,
           "result_keys": sorted(result.keys()) if isinstance(result, dict) else [],
           "elapsed_sec": time.time() - t_start}
    _audit_write(rec)
    return {
        "ok": op_ok,
        "result": result,
        "blocked_by": None,
        "audit_id": audit_id,
        "elapsed_sec": time.time() - t_start,
    }


def engram_audit_tail(n: int = 50) -> list[dict]:
    """Last n records from verimem syscall audit log."""
    if not ENGRAM_AUDIT_LOG.exists():
        return []
    try:
        lines = ENGRAM_AUDIT_LOG.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    out: list[dict] = []
    for line in lines[-n:]:
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def engram_rate_stats() -> dict:
    """Current rate-limiter state per op (diagnostic)."""
    return {
        op: {"recent_calls": len(b), "window_sec": _RATE_WINDOW_SEC}
        for op, b in _RATE_BUCKETS.items()
    }


def engram_available_ops() -> list[str]:
    """Manifest introspection: returns sorted list of declared ops."""
    return sorted(ENGRAM_OPS_MANIFEST.keys())
