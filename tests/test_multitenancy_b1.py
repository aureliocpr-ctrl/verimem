"""B-1 multi-tenancy (2026-06-08) — end-to-end tenant isolation through the MCP
surface. hippo_remember must SCOPE the stored fact's topic by user/agent/run;
hippo_facts_recall must ISOLATE (a user=alice query never returns user=bob's
fact). Zero-schema (topic prefix), backward-compatible (no scope dims = current
behavior).
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from engram import mcp_server
from engram.scope import scoped_topic
from engram.semantic import Fact, SemanticMemory


def _agent_with(sm):
    a = MagicMock()
    a.semantic = sm
    a.semantic.repo_root = None  # anti-confab gate -> format-only (no repo gate)
    return a


@pytest.mark.asyncio
async def test_remember_scopes_stored_topic(tmp_path, monkeypatch):
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    monkeypatch.setattr(mcp_server, "_ag", lambda: _agent_with(sm))

    await mcp_server.call_tool(
        "hippo_remember",
        {"proposition": "alice keeps the staging deploy key in vault path X",
         "topic": "ops", "user_id": "alice", "force_persist": True},
    )
    # The stored fact's topic must carry the user scope (regardless of status).
    with sm._connect() as c:
        topics = [r[0] for r in c.execute("SELECT topic FROM facts").fetchall()]
    assert topics, "fact was not stored at all"
    assert any(t.startswith("user:alice/") for t in topics), topics


@pytest.mark.asyncio
async def test_facts_recall_isolates_by_user(tmp_path, monkeypatch):
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    monkeypatch.setattr(mcp_server, "_ag", lambda: _agent_with(sm))
    # Same proposition for two tenants → identical embedding → both rank equally;
    # only the scope filter may separate them.
    prop = "the production database lives in eu-west-1"
    for who in ("alice", "bob"):
        sm.store(Fact(proposition=prop, topic=scoped_topic("infra", user_id=who),
                      status="model_claim", source_episodes=["e"]))

    res = await mcp_server.call_tool(
        "hippo_facts_recall", {"query": "production database region", "user_id": "alice", "k": 10},
    )
    rows = json.loads(res[0].text)["items"]
    assert rows, "alice should see her own fact"
    assert all(r["topic"].startswith("user:alice/") for r in rows), rows
    assert not any(r["topic"].startswith("user:bob/") for r in rows), rows


@pytest.mark.asyncio
async def test_facts_recall_no_scope_is_backward_compatible(tmp_path, monkeypatch):
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    monkeypatch.setattr(mcp_server, "_ag", lambda: _agent_with(sm))
    sm.store(Fact(proposition="kubernetes ingress uses nginx", topic="infra",
                  status="model_claim", source_episodes=["e"]))
    # No scope dims → unchanged behavior, the plain fact is returned.
    res = await mcp_server.call_tool(
        "hippo_facts_recall", {"query": "kubernetes ingress", "k": 5},
    )
    rows = json.loads(res[0].text)["items"]
    assert any(r["topic"] == "infra" for r in rows), rows


@pytest.mark.asyncio
async def test_facts_search_isolates_by_user(tmp_path, monkeypatch):
    # The keyword path must isolate too (not just semantic recall).
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    monkeypatch.setattr(mcp_server, "_ag", lambda: _agent_with(sm))
    for who in ("alice", "bob"):
        sm.store(Fact(proposition="vault token rotation policy", topic=scoped_topic("sec", user_id=who),
                      status="model_claim", source_episodes=["e"]))
    res = await mcp_server.call_tool(
        "hippo_facts_search", {"query": "vault token", "user_id": "alice", "limit": 50},
    )
    rows = json.loads(res[0].text)["items"]
    assert rows, "alice should see her own fact"
    assert all(r["topic"].startswith("user:alice/") for r in rows), rows
    assert not any(r["topic"].startswith("user:bob/") for r in rows), rows


@pytest.mark.asyncio
async def test_facts_recall_include_shared_returns_global(tmp_path, monkeypatch):
    # include_shared lets a tenant query also see UNSCOPED (global) facts.
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    monkeypatch.setattr(mcp_server, "_ag", lambda: _agent_with(sm))
    sm.store(Fact(proposition="company holiday calendar is public", topic="hr",
                  status="model_claim", source_episodes=["e"]))
    sm.store(Fact(proposition="alice private note about hr", topic=scoped_topic("hr", user_id="alice"),
                  status="model_claim", source_episodes=["e"]))
    # alice WITHOUT include_shared → only her own
    res = await mcp_server.call_tool(
        "hippo_facts_recall", {"query": "hr note calendar", "user_id": "alice", "k": 10})
    own = json.loads(res[0].text)["items"]
    assert all(r["topic"].startswith("user:alice/") for r in own), own
    # alice WITH include_shared → her own + the global one
    res2 = await mcp_server.call_tool(
        "hippo_facts_recall",
        {"query": "hr note calendar", "user_id": "alice", "include_shared": True, "k": 10})
    both = json.loads(res2[0].text)["items"]
    assert any(r["topic"] == "hr" for r in both), both


@pytest.mark.asyncio
async def test_facts_list_isolates_by_user(tmp_path, monkeypatch):
    # The "list" path must isolate too — else a tenant listing sees everyone.
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    monkeypatch.setattr(mcp_server, "_ag", lambda: _agent_with(sm))
    sm.store(Fact(proposition="alice item", topic=scoped_topic("t", user_id="alice"),
                  status="model_claim", source_episodes=["e"]))
    sm.store(Fact(proposition="bob item", topic=scoped_topic("t", user_id="bob"),
                  status="model_claim", source_episodes=["e"]))
    sm.store(Fact(proposition="global item", topic="t",
                  status="model_claim", source_episodes=["e"]))
    res = await mcp_server.call_tool("hippo_facts_list", {"user_id": "alice", "limit": 100})
    rows = json.loads(res[0].text)["items"]
    assert rows and all(r["topic"].startswith("user:alice/") for r in rows), rows
    # no scope -> sees all 3 (admin/backward-compat)
    res_all = await mcp_server.call_tool("hippo_facts_list", {"limit": 100})
    assert json.loads(res_all[0].text)["total"] == 3


def test_recall_topic_prefix_narrows_at_db_level(tmp_path):
    """Scale-completeness: SQL prefix narrowing means a tenant's facts are
    recalled even when buried under far more noise from other tenants — they
    compete only among the tenant's own rows, not the global top-k window.
    Deterministic (DB-level, not ranking-dependent). `_` in ids is a LIKE
    wildcard and MUST be escaped (ids allow underscores).
    """
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    for i in range(50):
        sm.store(Fact(proposition=f"shared infra note {i}", topic="user:bob/x",
                      status="model_claim", source_episodes=["e"]))
    for i in range(3):
        sm.store(Fact(proposition=f"shared infra note alice {i}", topic="user:alice/x",
                      status="model_claim", source_episodes=["e"]))
    # underscore-id row that must NOT be caught by a `user:a_x/` LIKE pattern
    sm.store(Fact(proposition="decoy underscore", topic="user:aXx/x",
                  status="model_claim", source_episodes=["e"]))
    hits = sm.recall("shared infra note", k=10, topic_prefix="user:alice/")
    assert hits, "alice's facts should be recalled"
    assert all(f.topic.startswith("user:alice/") for f, _ in hits), [f.topic for f, _ in hits]
    assert len(hits) == 3, f"expected exactly alice's 3 facts, got {len(hits)}"

    # underscore escaping: prefix with a literal underscore must not glob.
    sm.store(Fact(proposition="real underscore tenant", topic="user:a_x/x",
                  status="model_claim", source_episodes=["e"]))
    hits2 = sm.recall("underscore", k=10, topic_prefix="user:a_x/")
    assert all(f.topic.startswith("user:a_x/") for f, _ in hits2), [f.topic for f, _ in hits2]


@pytest.mark.asyncio
async def test_forget_scope_dry_run_then_delete_with_undo(tmp_path, monkeypatch):
    # mem0-parity delete_all(user_id): scoped forget. Safe — dry_run default,
    # reversible (each delete via delete_with_undo).
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    monkeypatch.setattr(mcp_server, "_ag", lambda: _agent_with(sm))
    for who in ("alice", "alice", "bob"):
        sm.store(Fact(proposition=f"note for {who}", topic=scoped_topic("t", user_id=who),
                      status="model_claim", source_episodes=["e"]))

    # dry-run (DEFAULT): preview only, nothing deleted.
    res = await mcp_server.call_tool("hippo_forget_scope", {"user_id": "alice"})
    p = json.loads(res[0].text)
    assert p["dry_run"] is True and p["would_delete"] == 2, p
    assert len(sm.all()) == 3, "dry-run must not delete"

    # actual delete (dry_run=False) — alice's 2 gone, bob's 1 stays.
    res2 = await mcp_server.call_tool("hippo_forget_scope", {"user_id": "alice", "dry_run": False})
    p2 = json.loads(res2[0].text)
    assert p2["dry_run"] is False and p2["removed"] == 2, p2
    assert len(p2["op_ids"]) == 2, p2
    remaining = sm.all()
    assert len(remaining) == 1 and remaining[0].topic.startswith("user:bob/"), [f.topic for f in remaining]

    # reversible: undoing one op restores one alice fact.
    await mcp_server.call_tool("hippo_undo_destructive_op", {"op_id": p2["op_ids"][0]})
    assert len(sm.all()) == 2, "undo should restore one deleted fact"


@pytest.mark.asyncio
async def test_remember_rejects_topic_scope_injection(tmp_path, monkeypatch):
    # SECURITY (audit 2026-06-09): the READ path trusts a leading user:/agent:/
    # run: prefix as the authoritative tenant tag, so a caller must NOT be able
    # to plant a fact in another tenant's scope by embedding that prefix in the
    # free-text topic without the matching scope kwarg. Isolation must hold on
    # WRITE, not only on read.
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    monkeypatch.setattr(mcp_server, "_ag", lambda: _agent_with(sm))
    res = await mcp_server.call_tool(
        "hippo_remember",
        {"proposition": "attacker planted instruction for the victim tenant",
         "topic": "user:victim/notes", "force_persist": True},  # NO user_id kwarg
    )
    assert "error" in json.loads(res[0].text), res[0].text
    # nothing landed in victim's scope
    with sm._connect() as c:
        topics = [r[0] for r in c.execute("SELECT topic FROM facts").fetchall()]
    assert not any(t.startswith("user:victim/") for t in topics), topics
    # and victim's scoped recall never sees the attacker's proposition
    res2 = await mcp_server.call_tool(
        "hippo_facts_recall",
        {"query": "attacker planted instruction", "user_id": "victim", "k": 10},
    )
    rows = json.loads(res2[0].text)["items"]
    assert not any("attacker" in r["proposition"] for r in rows), rows


@pytest.mark.asyncio
async def test_remember_allows_matching_topic_prefix(tmp_path, monkeypatch):
    # The guard must NOT break the legitimate idempotent case: an already-scoped
    # topic whose prefix MATCHES the supplied scope kwarg is fine (no double-wrap).
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    monkeypatch.setattr(mcp_server, "_ag", lambda: _agent_with(sm))
    res = await mcp_server.call_tool(
        "hippo_remember",
        {"proposition": "alice owns this note", "topic": "user:alice/notes",
         "user_id": "alice", "force_persist": True},
    )
    assert "error" not in json.loads(res[0].text), res[0].text
    with sm._connect() as c:
        topics = [r[0] for r in c.execute("SELECT topic FROM facts").fetchall()]
    assert topics == ["user:alice/notes"], topics  # no double-wrap


@pytest.mark.asyncio
async def test_forget_scope_refuses_unscoped_wipe(tmp_path, monkeypatch):
    # No scope dim => would target the whole corpus => MUST refuse.
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    monkeypatch.setattr(mcp_server, "_ag", lambda: _agent_with(sm))
    sm.store(Fact(proposition="precious", topic="t", status="model_claim", source_episodes=["e"]))
    res = await mcp_server.call_tool("hippo_forget_scope", {"dry_run": False})
    assert "error" in json.loads(res[0].text)
    assert len(sm.all()) == 1, "must not delete without an explicit scope"


@pytest.mark.asyncio
async def test_facts_by_agent_sees_canonical_and_legacy_scope(tmp_path, monkeypatch):
    # audit#3 (finding E): hippo_facts_by_agent used the legacy '^agent:' parser
    # and silently dropped facts under the canonical B-1 prefix
    # 'user:<u>/agent:<a>/...'. Routing through scope.matches_scope sees BOTH.
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    monkeypatch.setattr(mcp_server, "_ag", lambda: _agent_with(sm))
    sm.store(Fact(proposition="pentest finding alpha",
                  topic=scoped_topic("findings", user_id="alice", agent_id="pentester"),
                  status="model_claim", source_episodes=["e"]))
    sm.store(Fact(proposition="legacy agent finding beta",
                  topic="agent:pentester/legacy",
                  status="model_claim", source_episodes=["e"]))
    sm.store(Fact(proposition="other agent finding",
                  topic=scoped_topic("x", agent_id="reviewer"),
                  status="model_claim", source_episodes=["e"]))
    res = await mcp_server.call_tool(
        "hippo_facts_by_agent", {"agent_id": "pentester", "top_k": 50})
    prons = [f["proposition"] for f in json.loads(res[0].text)["facts"]]
    assert any("alpha" in p for p in prons), prons   # canonical user:/agent: form
    assert any("beta" in p for p in prons), prons     # legacy agent: form
    assert not any("other" in p for p in prons), prons  # different agent excluded
