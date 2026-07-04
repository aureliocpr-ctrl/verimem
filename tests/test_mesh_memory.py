"""Cycle 362 (2026-05-23) — MESH-MEMORY falsifiable contract test.

B4 NUCLEAR singolarità test: cross-instance vector-native recall via
vec_bus, NO plaintext exchange between agents.

FALSIFIABLE: agent_A queries semantic concept absent from its local
corpus but present in agent_B's corpus. The mesh_fuse() result must
contain remote_topk entry with cosine score > local_topk best score.

If remote_topk is empty OR no remote score exceeds local → FAIL.
Validates that:
  (1) vec_bus publish→fetch round-trip works
  (2) embedding flows but text does NOT
  (3) cross-corpus semantic union is computable
"""
from __future__ import annotations

import sqlite3
import struct
from pathlib import Path

import numpy as np
import pytest

EMBED_DIM = 384


def _vec_bus_available():
    try:
        from clp.agentos import vec_bus  # noqa: F401
        return True
    except ImportError:
        return False


def _build_corpus(db_path: Path, themes: dict[str, list[str]]) -> None:
    """Build a tiny semantic.db.

    themes maps theme_id → list of fact propositions. Each gets a real
    embedding via vec_bus.embed_text.
    """
    from clp.agentos.vec_bus import embed_text

    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("""
            CREATE TABLE facts (
                id TEXT PRIMARY KEY, topic TEXT, proposition TEXT,
                embedding BLOB, lineage_to TEXT, superseded_by TEXT,
                status TEXT
            )
        """)
        for theme_id, propositions in themes.items():
            for i, prop in enumerate(propositions):
                emb = embed_text(prop)
                fid = f"{theme_id}_{i}"
                conn.execute(
                    "INSERT INTO facts (id, topic, proposition, embedding) "
                    "VALUES (?, ?, ?, ?)",
                    (fid, theme_id, prop, emb),
                )
        conn.commit()
    finally:
        conn.close()


def test_local_topk_embeddings_returns_no_text(tmp_path: Path) -> None:
    """Local top-k returns (fact_id, embedding_bytes, score) — NOT proposition.

    This is the privacy primitive: peers only ever see embeddings.
    """
    if not _vec_bus_available():
        pytest.skip("vec_bus not available")
    from clp.agentos.vec_bus import embed_text

    from engram.mesh_memory import local_topk_embeddings

    db = tmp_path / "local.db"
    _build_corpus(db, {
        "fruit": ["Apple is a red fruit", "Banana is yellow"],
        "tech": ["Python is a programming language"],
    })
    query = embed_text("fruit color")
    results = local_topk_embeddings(db, query, k=3)
    assert len(results) > 0
    for fid, emb, score in results:
        # Falsifiable: emb is bytes (1536), NOT a proposition string.
        assert isinstance(emb, bytes)
        assert len(emb) == EMBED_DIM * 4
        assert isinstance(score, float)
        assert -1.0 <= score <= 1.0
        # Falsifiable: fact_id does not leak text content beyond the id namespace.
        # In real production, callers may need to map id → text on their side,
        # but the mesh primitive itself does not expose proposition.
        assert "Apple" not in fid and "Banana" not in fid


def test_mesh_publish_query_roundtrip(tmp_path: Path) -> None:
    """Publish a query embedding on vec_bus, fetch it back.

    Validates the basic vec_bus integration (without remote responder).
    """
    if not _vec_bus_available():
        pytest.skip("vec_bus not available")
    # Use unique channel per test to avoid pollution
    import time as _t

    from clp.agentos import vec_bus

    from engram.mesh_memory import mesh_fetch_recent, mesh_publish_query
    chan = f"mesh/test/{int(_t.time()*1000)}/req"

    # publish
    pub = mesh_publish_query("what is a fruit?", channel=chan)
    assert pub.get("ok"), f"publish failed: {pub}"
    qid = pub["msg_id"]

    # fetch (no peer filtering yet — own messages stay)
    fetched = mesh_fetch_recent(chan, since_ts=0.0, skip_own=False)
    assert any(m.get("msg_id") == qid for m in fetched), (
        "published message not visible on channel after publish"
    )

    # Cleanup
    try:
        vec_bus.vec_clean(chan, older_than_sec=0)
    except (AttributeError, Exception):  # noqa: BLE001
        pass


def test_mesh_cross_corpus_semantic_union(tmp_path: Path) -> None:
    """SINGOLARITÀ contract test (cycle 362).

    Two distinct corpora: A about programming, B about fruits.
    Query "what is a sweet fruit" → A has 0 relevant, B has matches.
    Expected: mesh_fuse() returns remote_topk with cosine > local_topk.

    This is the FALSIFIABLE empirical claim that cross-instance
    semantic recall via embedding-only exchange works.

    Implementation note: we simulate two agents in one process by
    running the responder synchronously after the query is published,
    rather than spawning a thread. The vec_bus is file-based so this
    is valid: any process that wrote to the channel before the
    fetching call will be observed.
    """
    if not _vec_bus_available():
        pytest.skip("vec_bus not available")
    from clp.agentos.vec_bus import embed_text

    from engram.mesh_memory import (
        local_topk_embeddings,
        mesh_fetch_recent,
        mesh_publish_query,
    )

    # Agent A corpus: programming-only
    db_a = tmp_path / "agent_a.db"
    _build_corpus(db_a, {
        "tech": [
            "Python is a programming language",
            "Rust has memory safety",
            "Compilers translate code",
        ],
    })

    # Agent B corpus: fruit-only
    db_b = tmp_path / "agent_b.db"
    _build_corpus(db_b, {
        "fruit": [
            "Apple is a sweet red fruit",
            "Mango is a tropical sweet fruit",
            "Grapes are small sweet fruits",
        ],
    })

    import time as _t
    chan_req = f"mesh/test/{int(_t.time()*1000)}/req"
    chan_rep = f"mesh/test/{int(_t.time()*1000)}/rep"

    # Step 1: agent A publishes query
    query_text = "what is a sweet fruit"
    pub = mesh_publish_query(query_text, channel=chan_req,
                              sender="agent_a_test")
    assert pub.get("ok")

    # Step 2: agent B (simulated synchronously) reads request,
    # computes local top-k from its OWN corpus, publishes responses.
    from clp.agentos.vec_bus import vec_send
    requests = mesh_fetch_recent(chan_req, since_ts=0.0, skip_own=False)
    assert len(requests) >= 1
    req_msg = requests[-1]
    # Decode query embedding
    import base64
    qvec = (
        req_msg.get("vec_bytes")
        if req_msg.get("vec_bytes") is not None
        else base64.b64decode(req_msg["vec_b64"])
    )
    # B's local top-k
    b_topk = local_topk_embeddings(db_b, qvec, k=2)
    assert len(b_topk) > 0
    # Publish each B-topk embedding to reply channel as agent B
    for fid, emb, score in b_topk:
        vec_send(chan_rep, emb, sender="agent_b_test",
                 origin_hint=f"reply-to:{req_msg['msg_id'][:8]}",
                 intent_tag=f"topk-resp:{score:.3f}")

    # Step 3: agent A's local top-k from its (programming-only) corpus
    qvec_a = embed_text(query_text)
    a_local = local_topk_embeddings(db_a, qvec_a, k=2)
    a_best_score = a_local[0][2] if a_local else 0.0

    # Step 4: agent A fetches replies (filter own A-sent)
    reply_msgs = mesh_fetch_recent(chan_rep, since_ts=0.0, skip_own=False)
    remote_scores: list[float] = []
    for m in reply_msgs:
        vec_b = m.get("vec_bytes")
        if vec_b is None and "vec_b64" in m:
            vec_b = base64.b64decode(m["vec_b64"])
        if not vec_b:
            continue
        rv = struct.unpack(f"<{EMBED_DIM}f", vec_b)
        qv = struct.unpack(f"<{EMBED_DIM}f", qvec_a)
        sc = float(sum(x * y for x, y in zip(rv, qv, strict=False)))
        remote_scores.append(sc)

    assert len(remote_scores) > 0, (
        "no remote responses observed — vec_bus or mesh fetch broken"
    )
    remote_best = max(remote_scores)

    # FALSIFIABLE assertion: remote (fruit) best > local (tech) best
    # because "sweet fruit" semantically aligned with B's corpus, NOT A's.
    assert remote_best > a_best_score, (
        f"MESH SINGULARITY FAILED: remote_best={remote_best:.4f} "
        f"not > local_best={a_best_score:.4f}. Cross-instance semantic "
        f"recall did not surface remote-better match."
    )

    # FALSIFIABLE privacy assertion: reply messages do NOT contain
    # the original B-side fact text. They contain only embedding bytes.
    for m in reply_msgs:
        # If the message dict serializes anywhere into a structure that
        # includes "Apple is a sweet red fruit" string, that's a leak.
        for v in m.values():
            if isinstance(v, str):
                assert "Apple is" not in v and "Mango is" not in v, (
                    f"Plaintext leaked: {v[:100]}"
                )

    # Cleanup channels
    try:
        from clp.agentos import vec_bus
        vec_bus.vec_clean(chan_req, older_than_sec=0)
        vec_bus.vec_clean(chan_rep, older_than_sec=0)
    except (AttributeError, Exception):  # noqa: BLE001
        pass


def test_mesh_resonant_merge_cycle363(tmp_path: Path) -> None:
    """Cycle 363 RESONANT-MERGE: Hopfield completion across local+remote.

    Falsifiable: with local corpus tech-only and remote (peer) supplying
    fruit embeddings for a 'sweet fruit' query, the completed pattern
    must cosine-align with the remote contribution more than with the
    original query (shift_cosine < 1.0 with meaningful magnitude shift).

    The cycle 362 mesh_fuse returned discrete top-k. Cycle 363
    mesh_resonant_merge returns ONE continuous embedding synthesizing
    local+remote — a genuinely new primitive for cross-agent semantic
    interpolation.
    """
    if not _vec_bus_available():
        pytest.skip("vec_bus not available")
    from clp.agentos.vec_bus import embed_text

    from engram.mesh_memory import mesh_resonant_merge

    q_vec = embed_text("what is a sweet fruit")
    # Local (tech-only): semantically distant from query
    local = [
        embed_text("Python is a programming language"),
        embed_text("Rust has memory safety"),
    ]
    # Remote (fruit, from peer): semantically aligned
    remote = [
        embed_text("Apple is a sweet red fruit"),
        embed_text("Mango is a tropical sweet fruit"),
    ]

    result = mesh_resonant_merge(q_vec, local, remote, beta=8.0)
    assert result["ok"], f"merge failed: {result}"
    assert result["n_local"] == 2
    assert result["n_remote"] == 2
    assert len(result["completed_bytes"]) == EMBED_DIM * 4
    assert 0.0 < result["shift_cosine"] <= 1.0

    # Attention should concentrate on remote (semantically aligned)
    local_att_total = sum(result["attention_local"])
    remote_att_total = sum(result["attention_remote"])
    assert remote_att_total > local_att_total, (
        f"Attention should focus on remote (fruit aligned). "
        f"local_att={local_att_total:.4f} remote_att={remote_att_total:.4f}"
    )

    # Cosine of completed vs each remote: must exceed cosine of completed vs each local
    completed = np.frombuffer(result["completed_bytes"], dtype=np.float32)
    q_arr = np.frombuffer(q_vec, dtype=np.float32)
    remote_cos = [float(np.dot(completed, np.frombuffer(e, dtype=np.float32)))
                  for e in remote]
    local_cos = [float(np.dot(completed, np.frombuffer(e, dtype=np.float32)))
                 for e in local]
    assert max(remote_cos) > max(local_cos), (
        f"completed must align with remote > local. "
        f"max_remote={max(remote_cos):.4f} max_local={max(local_cos):.4f}"
    )

    # Shift must be meaningful (completed moved away from raw query)
    raw_q_self_cos = float(np.dot(q_arr / np.linalg.norm(q_arr), q_arr / np.linalg.norm(q_arr)))
    assert raw_q_self_cos > 0.99  # sanity
    assert result["shift_cosine"] < 0.99, (
        f"completed pattern did not shift from query "
        f"(shift_cosine={result['shift_cosine']:.4f}) — no resonance"
    )
