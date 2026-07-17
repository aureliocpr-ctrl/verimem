"""Multi-tenant SCALE: a tenant-scoped recall must drive ``idx_facts_topic``
(O(N_tenant) B-tree prefix scan), never a full ``superseded_by`` scan
(O(N_total)). The pre-fix ``topic LIKE 'p%'`` could not use the index —
measured 203ms→0.16ms @1M rows / 10k tenants once forced onto the index
(arch-lab/sistema/multitenant_scan_v2.py). The half-open range also treats
``_`` as a LITERAL (no LIKE single-char glob), which is exactly the prefix
semantics the scope contract needs.
"""
from __future__ import annotations

from verimem.semantic import Fact, SemanticMemory, _topic_prefix_upper


def test_topic_prefix_upper_is_lexicographic_successor():
    assert _topic_prefix_upper("user:alice/") == "user:alice0"  # '/'(0x2f)->'0'(0x30)
    assert _topic_prefix_upper("project") == "projecu"
    assert _topic_prefix_upper("a") == "b"
    assert _topic_prefix_upper("") == ""


def test_range_bounds_match_exactly_the_prefix():
    # [p, p⁺) catches every string starting with p and nothing else, and '_' is
    # a LITERAL (the decoy 'user:aXx/' must NOT be caught by 'user:a_x/').
    p = "user:a_x/"
    up = _topic_prefix_upper(p)
    for inside in ("user:a_x/", "user:a_x/note", "user:a_x/zzz"):
        assert p <= inside < up, inside
    for outside in ("user:aXx/note", "user:b/x", "user:a_x", "user:a_w/"):
        assert not (p <= outside < up), outside


def test_scoped_recall_drives_topic_index(tmp_path):
    # EXPLAIN the exact shape the legacy scoped path emits: it must SEARCH via
    # idx_facts_topic, never a full SCAN / superseded_by scan.
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    for i in range(50):
        sm.store(Fact(proposition=f"note {i}", topic=f"user:u{i % 5}/n{i}",
                      status="model_claim", source_episodes=["e"]))
    with sm._connect() as c:
        plan = " ".join(str(r[-1]) for r in c.execute(
            "EXPLAIN QUERY PLAN SELECT * FROM facts INDEXED BY idx_facts_topic "
            "WHERE topic >= ? AND topic < ? AND superseded_by IS NULL",
            ("user:u3/", _topic_prefix_upper("user:u3/"))))
    assert "idx_facts_topic" in plan, plan
    assert "SCAN" not in plan, plan


def test_scoped_recall_still_isolates_and_finds(tmp_path):
    # end-to-end: the index-forced path still returns EXACTLY the tenant's rows
    # (correctness preserved alongside the O(N_tenant) lookup).
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    for i in range(20):
        sm.store(Fact(proposition=f"bob infra note {i}", topic="user:bob/x",
                      status="model_claim", source_episodes=["e"]))
    for i in range(3):
        sm.store(Fact(proposition=f"alice infra note {i}", topic="user:alice/x",
                      status="model_claim", source_episodes=["e"]))
    # underscore tenant: literal '_', must not glob
    sm.store(Fact(proposition="underscore tenant note", topic="user:a_x/x",
                  status="model_claim", source_episodes=["e"]))
    hits = sm.recall("infra note", k=10, topic_prefix="user:alice/")
    assert hits, "alice's facts should be recalled"
    assert all(f.topic.startswith("user:alice/") for f, _ in hits), [f.topic for f, _ in hits]
    assert len(hits) == 3, f"expected exactly alice's 3, got {len(hits)}"
    # the underscore prefix is literal: matches only user:a_x/, not user:aXx/
    hits_u = sm.recall("underscore", k=10, topic_prefix="user:a_x/")
    assert all(f.topic.startswith("user:a_x/") for f, _ in hits_u), [f.topic for f, _ in hits_u]


def test_exact_topic_and_prefix_concurrent(tmp_path):
    # Critic D: ``topic`` (exact) + ``topic_prefix`` supplied together must stay
    # correct under the INDEXED BY path — AND-intersection semantics, no crash,
    # no cross-tenant leak (verified: compat -> the one row, incompat -> empty).
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    for i in range(5):
        sm.store(Fact(proposition=f"alice note {i}", topic=f"user:alice/n{i}",
                      status="model_claim", source_episodes=["e"]))
    sm.store(Fact(proposition="bob note", topic="user:bob/n0",
                  status="model_claim", source_episodes=["e"]))
    # compatible: exact topic inside the prefix -> exactly that row
    hits = sm.recall("alice note", k=10, topic="user:alice/n2", topic_prefix="user:alice/")
    assert [f.topic for f, _ in hits] == ["user:alice/n2"], [f.topic for f, _ in hits]
    # incompatible: exact topic OUTSIDE the prefix -> empty (intersection), no crash/leak
    hits2 = sm.recall("note", k=10, topic="user:bob/n0", topic_prefix="user:alice/")
    assert hits2 == [], [f.topic for f, _ in hits2]
