"""Cycle 362 (2026-05-23) — MESH-MEMORY: cross-instance vector-native recall.

B4 NUCLEAR concatenazione 5 elementi → tesi nuova falsificabile:
  clp vec_bus (cross-process binary embedding broadcast, LOOP 356)
  + HippoAgent semantic.db (per-instance persistent embeddings)
  + clp syscall (kernel typed boundary)
  + SOS Jaccard partition metric (paper §3)
  + Modern Hopfield pattern completion (verimem.hopfield)
  ⇒ MESH-MEMORY: distributed semantic recall across multiple AI instances
    WITHOUT exchanging fact-text. Only embedding flow.

TESI FALSIFICABILE NUCLEAR (Aurelio carta bianca 2026-05-23):
  Two AI instances with DISTINCT local semantic.db corpora can perform
  joint semantic recall via embedding-only exchange on the vec_bus.
  Each instance publishes its query embedding; peer instances respond
  with their local top-k EMBEDDINGS (NOT the fact text). The querying
  instance fuses local+remote top-k via cosine into a unified ranking.

Singolarità claim: "mesh-memory" is to memory what mesh-network is to
networking — federated semantic union without central authority,
without text exchange, without DB replication. The vector IS the
recall primitive.

ANTI-CONFAB vs existing patterns:
  - Federated learning: shares gradient updates, NOT recall results.
  - Cross-corpus RAG: copies documents/chunks across stores.
  - LangChain multi-agent: text-mediated coordination.
  - Distributed vector DB (Weaviate cluster): single logical store,
    not multi-agent federation.
  - vec_bus alone (LOOP 356): point-to-point intent broadcast, NOT
    recall federation with top-k response semantics.

What is GENUINELY novel here: the recall RESULTS travel as raw
embeddings, not as fact text. The semantic intent of "give me your
top-3 closest to this query" is itself encoded in the query vector
on the mesh, and responses are pure float32 streams. The receiving
agent never sees the peer's plaintext memory.

FALSIFICATION TEST (cycle 362):
  Build two synthetic corpora A and B with distinct content.
  Agent_A queries "X" → publishes query embedding on mesh/recall.
  Agent_B reads channel, computes local top-1 cosine, publishes back.
  Falsifiable: agent_A's fused result includes B's top-1 vector
  with cosine > 0.3 when query is semantically aligned with B's content
  AND A's content does NOT contain that semantic neighbour.

Privacy implication: peer instances expose embeddings, NOT plaintext.
For untrusted federation, embedding-only exchange limits leakage
(though embeddings can be inverted in some regimes — caveat).

API:
  mesh_publish_query(text, channel="mesh/recall/req") -> {ok, msg_id}
  mesh_respond_topk(channel_req, channel_rep, semantic_db, k=5,
                    poll_interval=0.5, run_secs=10.0) -> daemon loop
  mesh_fetch_responses(channel_rep, since_ts) -> list[(sender, vec_b64, score)]
  mesh_fuse(query_text, semantic_db, channel_req="mesh/recall/req",
            channel_rep="mesh/recall/rep", wait_secs=2.0, k=5)
    -> unified top-k vectors from local + remote, cosine-ranked

Dependencies (clp.agentos.vec_bus): vec_send, vec_recv, cosine,
                                      embed_text.
"""
from __future__ import annotations

import sqlite3
import struct
import time
from pathlib import Path

EMBED_DIM = 384


def _vec_bus():
    """Lazy import of vec_bus to avoid hard dependency at import time."""
    try:
        from clp.agentos import vec_bus as _vb
        return _vb
    except ImportError:
        return None


def _cosine(a: bytes, b: bytes) -> float:
    """Cosine similarity between two L2-normalized 384-dim float32 byte blobs."""
    if len(a) != EMBED_DIM * 4 or len(b) != EMBED_DIM * 4:
        return 0.0
    av = struct.unpack(f"<{EMBED_DIM}f", a)
    bv = struct.unpack(f"<{EMBED_DIM}f", b)
    return float(sum(x * y for x, y in zip(av, bv, strict=False)))


def local_topk_embeddings(
    semantic_db: Path | str, query_vec_bytes: bytes, k: int = 5,
) -> list[tuple[str, bytes, float]]:
    """Return local top-k (fact_id, embedding_bytes, cosine_score).

    Pure embedding-space operation. The text proposition is NOT returned,
    only the embedding. This is the privacy-preserving primitive.

    Args:
        semantic_db: path to local semantic.db.
        query_vec_bytes: 1536-byte float32[384] L2-normalized.
        k: top-k to return.

    Returns:
        list of (fact_id, embedding_bytes, cosine_score) sorted descending.
        Empty list on DB missing / no facts with valid embeddings.
    """
    if len(query_vec_bytes) != EMBED_DIM * 4:
        return []
    p = Path(semantic_db)
    if not p.exists():
        return []
    conn = sqlite3.connect(str(p))
    try:
        rows = conn.execute(
            "SELECT id, embedding FROM facts "
            "WHERE (superseded_by IS NULL OR superseded_by = '') "
            "AND embedding IS NOT NULL "
            "AND length(embedding) = ?",
            (EMBED_DIM * 4,),
        ).fetchall()
    finally:
        conn.close()
    scored: list[tuple[str, bytes, float]] = []
    for fid, emb in rows:
        s = _cosine(query_vec_bytes, emb)
        scored.append((fid, emb, s))
    scored.sort(key=lambda r: r[2], reverse=True)
    return scored[:k]


def mesh_publish_query(
    text: str,
    channel: str = "mesh/recall/req",
    intent_tag: str = "query",
    sender: str | None = None,
) -> dict:
    """Publish a query text → embedding on the mesh request channel.

    Returns vec_bus.vec_send result dict.
    """
    vb = _vec_bus()
    if vb is None:
        return {"ok": False, "error": "clp.agentos.vec_bus not available"}
    return vb.vec_send(channel, text, sender=sender,
                       origin_hint=text[:80], intent_tag=intent_tag)


def mesh_fetch_recent(
    channel: str,
    since_ts: float = 0.0,
    skip_own: bool = True,
    own_sender: str | None = None,
) -> list[dict]:
    """Fetch recent messages on mesh channel since timestamp.

    Returns list of parsed messages (vec_bus format). Filters out own
    messages by default to avoid receiving back what we just sent.
    """
    vb = _vec_bus()
    if vb is None:
        return []
    # vec_bus.vec_recv returns list[(msg_id, vec_bytes, origin_hint)] historically.
    # For mesh we need the full message with sender + ts; use vec_recv raw.
    try:
        msgs = vb.vec_recv(channel, since_epoch=since_ts)
    except Exception:  # noqa: BLE001
        return []
    out: list[dict] = []
    if not msgs:
        return out
    own = own_sender or ""
    for m in msgs:
        # vec_recv may return tuples or dicts depending on version.
        if isinstance(m, dict):
            if skip_own and m.get("sender") == own:
                continue
            out.append(m)
        else:
            # tuple format — wrap minimally
            try:
                msg_id, vec_b, origin = m[0], m[1], (m[2] if len(m) > 2 else "")
            except (IndexError, TypeError):
                continue
            out.append({
                "msg_id": msg_id, "vec_bytes": vec_b,
                "origin_hint": origin, "sender": "unknown",
            })
    return out


def mesh_fuse_local_remote(
    query_text: str,
    semantic_db: Path | str,
    channel_req: str = "mesh/recall/req",
    channel_rep: str = "mesh/recall/rep",
    wait_secs: float = 2.0,
    k: int = 5,
) -> dict:
    """End-to-end mesh recall: publish query, wait for responses, fuse.

    Returns:
        {
          "ok": bool,
          "query_id": str,
          "local_topk": [(fact_id, score), ...],   # plaintext IDs OK locally
          "remote_topk": [(sender, msg_id, score), ...],  # no plaintext
          "fused_topk": [(source, ref, score), ...],
          "n_responses": int,
        }

    The MESH SINGULARITY: remote_topk returns only msg_ids + scores,
    NOT the remote plaintext fact content. Embedding flowed; text never did.
    """
    vb = _vec_bus()
    if vb is None:
        return {"ok": False, "error": "vec_bus unavailable"}

    # 1. Publish query
    pub = mesh_publish_query(query_text, channel=channel_req)
    if not pub.get("ok"):
        return {"ok": False, "error": "publish failed", "detail": pub}

    query_vec_bytes = vb.embed_text(query_text)

    # 2. Local top-k (instant)
    local = local_topk_embeddings(semantic_db, query_vec_bytes, k=k)
    local_topk = [(fid, score) for (fid, _emb, score) in local]

    # 3. Wait for remote responses on reply channel
    deadline = time.time() + wait_secs
    own = vb._instance_id() if hasattr(vb, "_instance_id") else None
    responses: list[dict] = []
    since = time.time() - wait_secs  # be lenient on prior responses too
    while time.time() < deadline:
        resp = mesh_fetch_recent(channel_rep, since_ts=since,
                                  skip_own=True, own_sender=own)
        responses = resp
        if responses:
            break
        time.sleep(0.2)

    # 4. Fuse: rank all (local + remote) by cosine vs query
    remote_topk: list[tuple[str, str, float]] = []
    for rmsg in responses:
        # Extract embedding bytes from response
        vec_b = rmsg.get("vec_bytes")
        if vec_b is None and "vec_b64" in rmsg:
            import base64
            vec_b = base64.b64decode(rmsg["vec_b64"])
        if not vec_b:
            continue
        score = _cosine(query_vec_bytes, vec_b)
        remote_topk.append((rmsg.get("sender", "unknown"),
                            rmsg.get("msg_id", ""), score))
    remote_topk.sort(key=lambda r: r[2], reverse=True)
    remote_topk = remote_topk[:k]

    # 5. Build fused: tagged source for caller distinction
    fused: list[tuple[str, str, float]] = []
    for fid, sc in local_topk:
        fused.append(("local", fid, sc))
    for sender, mid, sc in remote_topk:
        fused.append(("remote", f"{sender}/{mid}", sc))
    fused.sort(key=lambda r: r[2], reverse=True)
    fused_topk = fused[:k]

    return {
        "ok": True,
        "query_id": pub.get("msg_id"),
        "local_topk": local_topk,
        "remote_topk": remote_topk,
        "fused_topk": fused_topk,
        "n_responses": len(responses),
    }


def mesh_resonant_merge(
    query_vec_bytes: bytes,
    local_embeddings: list[bytes],
    remote_embeddings: list[bytes],
    beta: float = 8.0,
) -> dict:
    """Cycle 363 RESONANT-MERGE: Hopfield completion over local+remote field.

    Concatenates local + remote embeddings into a unified pattern matrix
    M ∈ R^(N×384), runs modern Hopfield (Ramsauer 2020) completion with
    the query as cue:

        completed = M.T @ softmax(β · M @ query)

    Returns the soft mixture vector — semantically positioned between
    local and remote contributions weighted by their cosine relevance.

    GENUINELY NOVEL beyond cycle 362 mesh_fuse:
    - mesh_fuse: returns ranked top-k (discrete selection)
    - mesh_resonant_merge: returns CONTINUOUS interpolation —
      a single embedding that synthesizes local+remote insight, usable
      as expanded query for second-stage retrieval or as direct
      context-vector injection for the next inference step.

    Falsifiable: the completed vector should have higher cosine to the
    semantically-aligned remote contribution than the original query,
    when local corpus has zero relevant matches but remote has them.

    Args:
        query_vec_bytes: 1536-byte float32[384] L2-normalized query.
        local_embeddings: list of local embedding bytes (this agent).
        remote_embeddings: list of remote embedding bytes (peers).
        beta: Hopfield inverse-temperature. Higher = harder argmax.

    Returns:
        {
          "ok": bool,
          "completed_bytes": bytes (1536) — soft mixture pattern,
          "attention_local": list[float] — weight per local pattern,
          "attention_remote": list[float] — weight per remote pattern,
          "shift_cosine": float — cos(completed, query),
          "n_local": int, "n_remote": int,
        }

    The shift_cosine < 1.0 means completion moved the query away from
    its original direction — indicates the field has pulled it toward
    a non-trivial mixture. shift_cosine ≈ 1.0 means no resonance.
    """
    import struct as _st

    import numpy as np

    if len(query_vec_bytes) != EMBED_DIM * 4:
        return {"ok": False, "error": f"query must be {EMBED_DIM*4} bytes"}

    all_embs = local_embeddings + remote_embeddings
    if not all_embs:
        return {"ok": False, "error": "no embeddings to merge"}

    # Build M ∈ R^(N×384)
    rows = []
    for emb in all_embs:
        if len(emb) != EMBED_DIM * 4:
            continue
        rows.append(_st.unpack(f"<{EMBED_DIM}f", emb))
    if not rows:
        return {"ok": False, "error": "no valid embeddings"}
    M = np.asarray(rows, dtype=np.float32)
    n_total = M.shape[0]
    n_local = sum(1 for e in local_embeddings if len(e) == EMBED_DIM * 4)
    n_remote = n_total - n_local

    q = np.asarray(_st.unpack(f"<{EMBED_DIM}f", query_vec_bytes),
                    dtype=np.float32)
    # L2 normalize q (defensive)
    qn = float(np.linalg.norm(q))
    if qn > 0:
        q = q / qn

    # Hopfield completion
    scores = M @ q  # (N,)
    s_max = float(np.max(scores))
    z = np.exp(beta * (scores - s_max))
    s = float(z.sum())
    weights = z / s if s > 0 else np.full_like(z, 1.0 / z.size)
    completed = M.T @ weights  # (384,)
    # Re-normalize completed for consistent cosine semantics
    cn = float(np.linalg.norm(completed))
    if cn > 0:
        completed = completed / cn

    completed_bytes = _st.pack(f"<{EMBED_DIM}f", *completed.tolist())
    shift_cosine = float(np.dot(completed, q))

    return {
        "ok": True,
        "completed_bytes": completed_bytes,
        "attention_local": [float(weights[i]) for i in range(n_local)],
        "attention_remote": [float(weights[i]) for i in range(n_local, n_total)],
        "shift_cosine": shift_cosine,
        "n_local": n_local,
        "n_remote": n_remote,
    }


def mesh_respond_topk(
    semantic_db: Path | str,
    channel_req: str = "mesh/recall/req",
    channel_rep: str = "mesh/recall/rep",
    k: int = 5,
    poll_interval: float = 0.5,
    run_secs: float = 10.0,
) -> dict:
    """Daemon: listen on req channel, respond with local top-k embeddings.

    Runs until run_secs elapsed. For each new request message, computes
    local top-k cosine matches on the given semantic.db and publishes
    each as a separate response on the reply channel (sender preserved
    as own instance_id).

    Returns aggregate counters.
    """
    vb = _vec_bus()
    if vb is None:
        return {"ok": False, "error": "vec_bus unavailable"}

    own = vb._instance_id() if hasattr(vb, "_instance_id") else "responder"
    t_start = time.time()
    deadline = t_start + run_secs
    n_req_handled = 0
    n_resp_published = 0
    seen_msg_ids: set[str] = set()

    while time.time() < deadline:
        msgs = mesh_fetch_recent(channel_req, since_ts=t_start,
                                  skip_own=True, own_sender=own)
        for m in msgs:
            mid = m.get("msg_id", "")
            if mid in seen_msg_ids:
                continue
            seen_msg_ids.add(mid)
            n_req_handled += 1
            vec_b = m.get("vec_bytes")
            if vec_b is None and "vec_b64" in m:
                import base64
                vec_b = base64.b64decode(m["vec_b64"])
            if not vec_b:
                continue
            local = local_topk_embeddings(semantic_db, vec_b, k=k)
            for fid, emb, score in local:
                vb.vec_send(channel_rep, emb, sender=own,
                            origin_hint=f"reply-to:{mid[:8]}",
                            intent_tag=f"topk-resp:{score:.3f}")
                n_resp_published += 1
        time.sleep(poll_interval)

    return {
        "ok": True,
        "elapsed_s": time.time() - t_start,
        "n_req_handled": n_req_handled,
        "n_resp_published": n_resp_published,
        "responder_id": own,
    }
