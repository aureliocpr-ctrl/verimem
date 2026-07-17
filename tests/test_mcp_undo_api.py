"""Cycle 2026-05-27 round 13 P0c — MCP undo API exposure pytest.

Verifies hippo_fact_forget_with_undo / hippo_undo_destructive_op /
hippo_undo_list are wired to the dispatcher and return correctly shaped
responses on the real schema-v7 SemanticMemory.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from verimem import mcp_server
from verimem.semantic import Fact, SemanticMemory


@pytest.fixture
def real_sm(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> SemanticMemory:
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    # Seed one fact for forget tests.
    sm.store(Fact(
        id="testfact00abcd",
        proposition="A throwaway fact for undo API tests.",
        topic="test/mcp_undo",
        confidence=0.9,
        verified_by=[],
        status="model_claim",
    ))

    class _FakeAgent:
        def __init__(self) -> None:
            self.semantic = sm

    monkeypatch.setattr(mcp_server, "_ag", lambda: _FakeAgent())
    monkeypatch.delenv("ENGRAM_VALIDATE_DEFAULT", raising=False)
    return sm


async def _invoke(name: str, arguments: dict | None = None) -> dict[str, Any]:
    from mcp.types import CallToolRequest, CallToolRequestParams
    handler = mcp_server.server.request_handlers[CallToolRequest]
    req = CallToolRequest(
        method="tools/call",
        params=CallToolRequestParams(name=name, arguments=arguments or {}),
    )
    result = await handler(req)
    payload = result.root if hasattr(result, "root") else result
    text = next(c.text for c in payload.content if hasattr(c, "text"))
    return json.loads(text)


class TestSchemaSurface:
    @pytest.mark.asyncio
    async def test_three_undo_tools_listed(self, real_sm: SemanticMemory):
        tools = await mcp_server.list_tools()
        names = {t.name for t in tools}
        for required in (
            "hippo_fact_forget_with_undo",
            "hippo_undo_destructive_op",
            "hippo_undo_list",
        ):
            assert required in names, f"missing tool: {required}"


class TestForgetWithUndoFlow:
    @pytest.mark.asyncio
    async def test_forget_returns_op_id(self, real_sm: SemanticMemory):
        out = await _invoke(
            "hippo_fact_forget_with_undo",
            {"fact_id": "testfact00abcd"},
        )
        assert out["ok"] is True
        assert out["removed"] is True
        assert out["op_id"] is not None
        assert len(out["op_id"]) == 16

    @pytest.mark.asyncio
    async def test_undo_round_trip_restores(self, real_sm: SemanticMemory):
        # Forget.
        forget_out = await _invoke(
            "hippo_fact_forget_with_undo",
            {"fact_id": "testfact00abcd"},
        )
        op_id = forget_out["op_id"]
        # Undo.
        undo_out = await _invoke(
            "hippo_undo_destructive_op", {"op_id": op_id},
        )
        assert undo_out["ok"] is True
        assert undo_out["action"] == "restored"
        # Verify fact is back via direct DB inspect.
        import sqlite3
        conn = sqlite3.connect(str(real_sm.db_path), timeout=5)
        cur = conn.cursor()
        cur.execute("SELECT proposition FROM facts WHERE id = ?",
                     ("testfact00abcd",))
        row = cur.fetchone()
        conn.close()
        assert row is not None
        assert "throwaway fact" in row[0]

    @pytest.mark.asyncio
    async def test_forget_missing_fact_no_op(self, real_sm: SemanticMemory):
        out = await _invoke(
            "hippo_fact_forget_with_undo",
            {"fact_id": "ghost000000abcd"},
        )
        assert out["ok"] is True
        assert out["removed"] is False
        assert out["op_id"] is None


class TestUndoList:
    @pytest.mark.asyncio
    async def test_lists_recent_undoable(self, real_sm: SemanticMemory):
        # Pre-state: 0 ops.
        out0 = await _invoke("hippo_undo_list", {})
        assert out0["ok"] is True
        assert out0["items"] == []
        # Forget creates one op.
        await _invoke(
            "hippo_fact_forget_with_undo",
            {"fact_id": "testfact00abcd"},
        )
        out1 = await _invoke("hippo_undo_list", {})
        assert len(out1["items"]) == 1
        assert out1["items"][0]["op_type"] == "forget"
        assert out1["items"][0]["fact_id"] == "testfact00abcd"


class TestUndoErrors:
    @pytest.mark.asyncio
    async def test_undo_unknown_op_id(self, real_sm: SemanticMemory):
        out = await _invoke(
            "hippo_undo_destructive_op",
            {"op_id": "doesnotexist0000"},
        )
        assert out["ok"] is False
        assert out["action"] == "not_found"

    @pytest.mark.asyncio
    async def test_undo_empty_op_id_rejected(self, real_sm: SemanticMemory):
        out = await _invoke("hippo_undo_destructive_op", {"op_id": ""})
        assert "error" in out

    @pytest.mark.asyncio
    async def test_double_undo_already_undone(self, real_sm: SemanticMemory):
        forget_out = await _invoke(
            "hippo_fact_forget_with_undo",
            {"fact_id": "testfact00abcd"},
        )
        op_id = forget_out["op_id"]
        r1 = await _invoke("hippo_undo_destructive_op", {"op_id": op_id})
        assert r1["action"] == "restored"
        r2 = await _invoke("hippo_undo_destructive_op", {"op_id": op_id})
        assert r2["action"] == "already_undone"
