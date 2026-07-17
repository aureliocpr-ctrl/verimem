"""Audit 3-round R1 #2 (security, multi-tenant): single-id fact delete must be
scope-gated.

hippo_fact_forget / hippo_fact_forget_with_undo deleted by raw id with ZERO
scope check, while hippo_forget_scope (right below) enforces matches_scope. In a
multi-tenant deployment tenant B could delete tenant A's fact by id — contradicts
the README's per-tenant isolation. Fix: when the caller supplies a scope
(user_id/agent_id/run_id), refuse to delete a fact outside that scope; unscoped
(admin) callers keep raw-id delete.
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from verimem import mcp_server
from verimem.scope import scoped_topic
from verimem.semantic import Fact, SemanticMemory


def _agent_with(sm: SemanticMemory) -> MagicMock:
    a = MagicMock()
    a.semantic = sm
    a.semantic.repo_root = None
    return a


def _alice_fact() -> Fact:
    return Fact(proposition="alice private note", status="model_claim",
                topic=scoped_topic("notes", user_id="alice"), source_episodes=["e"])


@pytest.mark.asyncio
async def test_fact_forget_rejects_cross_tenant_delete(tmp_path, monkeypatch):
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    monkeypatch.setattr(mcp_server, "_ag", lambda: _agent_with(sm))
    alice = _alice_fact()
    sm.store(alice)
    res = await mcp_server.call_tool(
        "hippo_fact_forget", {"fact_id": alice.id, "user_id": "bob"})
    assert "error" in json.loads(res[0].text), res[0].text
    assert sm.get(alice.id) is not None, "alice's fact must survive bob's delete"


@pytest.mark.asyncio
async def test_fact_forget_allows_in_scope_delete(tmp_path, monkeypatch):
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    monkeypatch.setattr(mcp_server, "_ag", lambda: _agent_with(sm))
    alice = _alice_fact()
    sm.store(alice)
    res = await mcp_server.call_tool(
        "hippo_fact_forget", {"fact_id": alice.id, "user_id": "alice"})
    assert "error" not in json.loads(res[0].text), res[0].text
    assert sm.get(alice.id) is None, "alice may delete her own fact"


@pytest.mark.asyncio
async def test_fact_forget_unscoped_admin_still_deletes(tmp_path, monkeypatch):
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    monkeypatch.setattr(mcp_server, "_ag", lambda: _agent_with(sm))
    alice = _alice_fact()
    sm.store(alice)
    res = await mcp_server.call_tool("hippo_fact_forget", {"fact_id": alice.id})
    assert "error" not in json.loads(res[0].text), res[0].text
    assert sm.get(alice.id) is None, "unscoped admin keeps raw-id delete"


@pytest.mark.asyncio
async def test_fact_forget_with_undo_is_also_scope_gated(tmp_path, monkeypatch):
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    monkeypatch.setattr(mcp_server, "_ag", lambda: _agent_with(sm))
    alice = _alice_fact()
    sm.store(alice)
    res = await mcp_server.call_tool(
        "hippo_fact_forget_with_undo", {"fact_id": alice.id, "user_id": "bob"})
    assert "error" in json.loads(res[0].text), res[0].text
    assert sm.get(alice.id) is not None, "with_undo must also block cross-tenant"
