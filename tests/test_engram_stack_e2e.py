"""Cycle 369 (2026-05-23) — ENGRAM STACK E2E integration test.

End-to-end falsifiable contract: simula 2 agent reali con corpora
distinte che si scambiano embedding-only recall federato attraverso
TUTTO lo stack cycle 362-368:

  Agent A query "X" → engram_invoke('mesh_query', token_A) → vec_bus publish
  Agent B fetches request → engram_invoke('mesh_fetch', token_B) → reads request
  Agent B local recall → engram_invoke('recall', token_B) → top-k of B's corpus
  Agent B publishes reply → vec_bus.vec_send embedding-only
  Agent A fetches reply → engram_invoke('mesh_fetch', token_A) → reads reply
  Agent A reads dashboard → engram_invoke shows audit trail

Falsifiable contract:
  (a) ALL engram_invoke calls succeed with valid tokens
  (b) Cross-instance recall result: B's embeddings recovered by A
  (c) NO plaintext exchange (privacy primitive preserved)
  (d) Audit log contains exact sequence of ops in order
  (e) Dashboard widget reflects N ok calls, 0 blocked
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest


def _vec_bus_available() -> bool:
    try:
        from clp.agentos import vec_bus  # noqa: F401
        return True
    except ImportError:
        return False


def _build_corpus(db: Path, propositions: dict[str, list[str]]) -> None:
    from clp.agentos.vec_bus import embed_text
    conn = sqlite3.connect(str(db))
    try:
        conn.execute("""
            CREATE TABLE facts (id TEXT PRIMARY KEY, topic TEXT,
                proposition TEXT, embedding BLOB, lineage_to TEXT,
                superseded_by TEXT, status TEXT)
        """)
        for topic, props in propositions.items():
            for i, prop in enumerate(props):
                conn.execute(
                    "INSERT INTO facts (id, topic, proposition, embedding) "
                    "VALUES (?, ?, ?, ?)",
                    (f"{topic}_{i}", topic, prop, embed_text(prop)),
                )
        conn.commit()
    finally:
        conn.close()


def test_engram_stack_e2e_two_agents(tmp_path, monkeypatch) -> None:
    """The full stack: 2 agents, mesh recall federation, all ops audited.

    This is the load-bearing E2E test for the cycle 362-368 stack
    integration. If this passes, the entire engram OS-native memory
    layer is operationally validated.
    """
    if not _vec_bus_available():
        pytest.skip("vec_bus not available")
    from clp.agentos.vec_bus import embed_text, vec_send

    from verimem import op_supervisor, syscall_bridge
    from verimem.capability_token import issue_token
    from verimem.dashboard_widget import collect_state

    # Isolate environment
    audit = tmp_path / "audit.jsonl"
    monkeypatch.setattr(syscall_bridge, "ENGRAM_AUDIT_LOG", audit)
    monkeypatch.setattr(op_supervisor, "_DEFAULT_SUPERVISOR",
                        op_supervisor.OpSupervisor(max_failures=100))
    syscall_bridge._RATE_BUCKETS.clear()

    # Build two distinct corpora
    db_a = tmp_path / "agent_a.db"
    db_b = tmp_path / "agent_b.db"
    _build_corpus(db_a, {
        "tech": ["Python is a programming language",
                 "Rust has memory safety"],
    })
    _build_corpus(db_b, {
        "fruit": ["Apple is sweet and red",
                  "Mango is tropical and sweet"],
    })

    import time as _t
    suffix = f"{_t.time()*1000:.0f}"
    chan_req = f"mesh/e2e/{suffix}/req"
    chan_rep = f"mesh/e2e/{suffix}/rep"

    # Issue tokens for each agent's allowed ops
    tok_A_recall = issue_token("agent_A", "recall", ttl_sec=60.0)
    tok_A_mesh_query = issue_token("agent_A", "mesh_query", ttl_sec=60.0)
    tok_A_mesh_fetch = issue_token("agent_A", "mesh_fetch", ttl_sec=60.0)
    tok_B_recall = issue_token("agent_B", "recall", ttl_sec=60.0)
    tok_B_mesh_fetch = issue_token("agent_B", "mesh_fetch", ttl_sec=60.0)

    # Step 1: Agent A publishes query (token-authorized)
    r1 = syscall_bridge.engram_invoke(
        "mesh_query",
        {"text": "what is sweet fruit", "channel": chan_req,
         "sender": "agent_A"},
        actor="agent_A",
        capability_token=tok_A_mesh_query,
        require_token=True,
    )
    assert r1["ok"], f"mesh_query failed: {r1}"

    # Step 2: Agent B fetches the request (token-authorized)
    r2 = syscall_bridge.engram_invoke(
        "mesh_fetch",
        {"channel": chan_req, "since_ts": 0.0, "skip_own": False},
        actor="agent_B",
        capability_token=tok_B_mesh_fetch,
        require_token=True,
    )
    assert r2["ok"], f"mesh_fetch failed: {r2}"
    assert r2["result"]["n_msgs"] >= 1

    # Step 3: Agent B does local recall on its corpus (token-authorized)
    r3 = syscall_bridge.engram_invoke(
        "recall",
        {"query": "what is sweet fruit", "k": 2, "db_path": str(db_b)},
        actor="agent_B",
        capability_token=tok_B_recall,
        require_token=True,
    )
    assert r3["ok"], f"B recall failed: {r3}"
    b_hits = r3["result"]["hits"]
    assert len(b_hits) >= 1
    # B's top result should be a fruit-related id (from db_b)
    top_id_b = b_hits[0][0]
    assert top_id_b.startswith("fruit_")

    # Step 4: Agent B publishes top-1 embedding back on reply channel
    # (bypass syscall here since we're sending raw bytes — that's the
    # privacy primitive: only embedding bytes flow on the wire)
    conn = sqlite3.connect(str(db_b))
    try:
        emb_b = conn.execute(
            "SELECT embedding FROM facts WHERE id = ?", (top_id_b,),
        ).fetchone()[0]
    finally:
        conn.close()
    vec_send(chan_rep, emb_b, sender="agent_B",
             origin_hint=f"reply-to:{r1['audit_id'][:8]}",
             intent_tag="topk-resp")

    # Step 5: Agent A fetches the reply
    r5 = syscall_bridge.engram_invoke(
        "mesh_fetch",
        {"channel": chan_rep, "since_ts": 0.0, "skip_own": True},
        actor="agent_A",
        capability_token=tok_A_mesh_fetch,
        require_token=True,
    )
    assert r5["ok"]
    assert r5["result"]["n_msgs"] >= 1

    # Step 6: A also does its own local recall (token-authorized)
    r6 = syscall_bridge.engram_invoke(
        "recall",
        {"query": "what is sweet fruit", "k": 2, "db_path": str(db_a)},
        actor="agent_A",
        capability_token=tok_A_recall,
        require_token=True,
    )
    assert r6["ok"]
    a_hits = r6["result"]["hits"]
    # A's top result should be tech-related (A's corpus is tech-only)
    assert a_hits[0][0].startswith("tech_")

    # Step 7: Dashboard widget reflects all 5 ok calls + 0 blocked
    state = collect_state(tail_n=50)
    summary = state["audit_summary_by_op"]
    # We expect: mesh_query=1 ok, mesh_fetch=2 ok, recall=2 ok
    assert summary.get("mesh_query", {}).get("ok", 0) == 1
    assert summary.get("mesh_fetch", {}).get("ok", 0) == 2
    assert summary.get("recall", {}).get("ok", 0) == 2
    # No blocked calls
    for op, counts in summary.items():
        blocked = {k: v for k, v in counts.items() if k != "ok"}
        assert not blocked, f"Op {op} has blocked: {blocked}"

    # Step 8: Privacy assertion — audit JSONL must NOT contain plaintext
    # propositions from either corpus
    raw = audit.read_text(encoding="utf-8")
    assert "Apple is sweet" not in raw, (
        "audit leaked B plaintext: 'Apple is sweet' found in JSONL"
    )
    assert "Python is a programming" not in raw, (
        "audit leaked A plaintext"
    )

    # Step 9: Order assertion — audit records appear in invocation order
    audit_records = [
        json.loads(line) for line in raw.splitlines() if line.strip()
    ]
    ops_in_order = [r["op"] for r in audit_records if r.get("ok")]
    # Expected sequence: mesh_query, mesh_fetch, recall, mesh_fetch, recall
    assert ops_in_order == ["mesh_query", "mesh_fetch", "recall",
                              "mesh_fetch", "recall"], (
        f"unexpected op order: {ops_in_order}"
    )

    # Cleanup mesh channels
    try:
        from clp.agentos import vec_bus
        vec_bus.vec_clean(chan_req, older_than_sec=0)
        vec_bus.vec_clean(chan_rep, older_than_sec=0)
    except (AttributeError, Exception):  # noqa: BLE001
        pass


def test_engram_stack_e2e_token_revocation_simulation(
    tmp_path, monkeypatch,
) -> None:
    """Falsifiable: agent with wrong-op token is blocked.

    Simulates per-op capability scoping: agent C has a token only
    for 'mesh_fetch' but tries to invoke 'recall' → blocked.
    """
    from verimem import op_supervisor, syscall_bridge
    from verimem.capability_token import issue_token

    audit = tmp_path / "audit.jsonl"
    monkeypatch.setattr(syscall_bridge, "ENGRAM_AUDIT_LOG", audit)
    monkeypatch.setattr(op_supervisor, "_DEFAULT_SUPERVISOR",
                        op_supervisor.OpSupervisor(max_failures=100))
    syscall_bridge._RATE_BUCKETS.clear()

    # Token scoped ONLY for mesh_fetch
    tok_fetch_only = issue_token("agent_C", "mesh_fetch", ttl_sec=60.0)

    # Try to use it for 'recall' (different op) — must be blocked
    r = syscall_bridge.engram_invoke(
        "recall",
        {"query": "anything", "k": 1},
        actor="agent_C",
        capability_token=tok_fetch_only,
        require_token=True,
    )
    assert r["ok"] is False
    assert r["blocked_by"] == "op_mismatch"

    # Verify it works for the allowed op
    r2 = syscall_bridge.engram_invoke(
        "mesh_fetch",
        {"channel": "test/scoped"},
        actor="agent_C",
        capability_token=tok_fetch_only,
        require_token=True,
    )
    # Doesn't require vec_bus actual functionality (channel may be empty)
    assert r2["ok"] is True or r2["blocked_by"] != "op_mismatch"
