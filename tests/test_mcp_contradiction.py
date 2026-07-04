"""Cycle #110.B — MCP dispatch tests for the contradiction tools.

Tests hippo_contradictions_scan / _list / _resolve through the real
MCP dispatch handler with a real ``SemanticMemory`` (tmp_path) so we
exercise the persistence layer end-to-end.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from engram import mcp_server
from engram.semantic import Fact, SemanticMemory


class _FakeAgent:
    def __init__(self, sm: SemanticMemory) -> None:
        self.semantic = sm


async def _invoke_tool(name: str, arguments: dict[str, Any] | None = None):
    from mcp.types import CallToolRequest, CallToolRequestParams
    handler = mcp_server.server.request_handlers[CallToolRequest]
    req = CallToolRequest(
        method="tools/call",
        params=CallToolRequestParams(name=name, arguments=arguments or {}),
    )
    result = await handler(req)
    payload = result.root if hasattr(result, "root") else result
    return [c.text for c in payload.content if hasattr(c, "text")]


@pytest.fixture
def agent_with_clash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> _FakeAgent:
    sm = SemanticMemory(db_path=tmp_path / "sm.db")
    sm.store(Fact(id="a", proposition="NEXUS has 17280 tests",
                   topic="project/nexus/test-count", confidence=0.95))
    sm.store(Fact(id="b", proposition="NEXUS has 10000 tests",
                   topic="project/nexus/test-count", confidence=0.9))
    agent = _FakeAgent(sm)
    monkeypatch.setattr(mcp_server, "_ag", lambda: agent)
    return agent


def _payload(blocks: list[str]) -> dict[str, Any]:
    return json.loads(blocks[0])


# ---------------------------------------------------------------------------


class TestContradictionsScan:

    @pytest.mark.asyncio
    async def test_tools_are_listed(
        self, agent_with_clash: _FakeAgent,
    ) -> None:
        from mcp.types import ListToolsRequest, PaginatedRequestParams
        handler = mcp_server.server.request_handlers[ListToolsRequest]
        result = await handler(ListToolsRequest(
            method="tools/list", params=PaginatedRequestParams(),
        ))
        payload = result.root if hasattr(result, "root") else result
        names = {tool.name for tool in payload.tools}
        for n in (
            "hippo_contradictions_scan",
            "hippo_contradictions_list",
            "hippo_contradictions_resolve",
        ):
            assert n in names, f"missing tool: {n}"

    @pytest.mark.asyncio
    async def test_scan_detects_and_persists(
        self, agent_with_clash: _FakeAgent,
    ) -> None:
        blocks = await _invoke_tool("hippo_contradictions_scan", {})
        payload = _payload(blocks)
        assert payload["new_detected"] >= 1
        assert payload["total_unresolved"] >= 1
        assert "numeric_clash" in payload["kinds"]

    @pytest.mark.asyncio
    async def test_scan_is_idempotent_via_mcp(
        self, agent_with_clash: _FakeAgent,
    ) -> None:
        first = _payload(await _invoke_tool("hippo_contradictions_scan", {}))
        second = _payload(await _invoke_tool("hippo_contradictions_scan", {}))
        assert second["new_detected"] == 0
        assert second["already_known"] >= 1
        assert second["total_unresolved"] == first["total_unresolved"]


class TestContradictionsList:

    @pytest.mark.asyncio
    async def test_list_after_scan_returns_pair(
        self, agent_with_clash: _FakeAgent,
    ) -> None:
        await _invoke_tool("hippo_contradictions_scan", {})
        payload = _payload(await _invoke_tool("hippo_contradictions_list", {}))
        assert payload["total_unresolved"] >= 1
        ids = {it["id"] for it in payload["items"]}
        assert len(ids) >= 1
        # The detected pair should reference our seeded facts.
        for it in payload["items"]:
            assert {it["fact_a_id"], it["fact_b_id"]} <= {"a", "b"}

    @pytest.mark.asyncio
    async def test_list_default_excludes_resolved(
        self, agent_with_clash: _FakeAgent,
    ) -> None:
        await _invoke_tool("hippo_contradictions_scan", {})
        listing = _payload(
            await _invoke_tool("hippo_contradictions_list", {}),
        )
        cid = listing["items"][0]["id"]
        await _invoke_tool(
            "hippo_contradictions_resolve",
            {"contradiction_id": cid, "note": "kept fact a"},
        )
        after = _payload(await _invoke_tool("hippo_contradictions_list", {}))
        assert all(it["id"] != cid for it in after["items"])

    @pytest.mark.asyncio
    async def test_list_with_include_resolved_returns_all(
        self, agent_with_clash: _FakeAgent,
    ) -> None:
        await _invoke_tool("hippo_contradictions_scan", {})
        listing = _payload(
            await _invoke_tool("hippo_contradictions_list", {}),
        )
        cid = listing["items"][0]["id"]
        await _invoke_tool(
            "hippo_contradictions_resolve",
            {"contradiction_id": cid, "note": "kept fact a"},
        )
        full = _payload(await _invoke_tool(
            "hippo_contradictions_list",
            {"include_resolved": True},
        ))
        assert any(it["id"] == cid for it in full["items"])


class TestContradictionsResolve:

    @pytest.mark.asyncio
    async def test_resolve_missing_id_rejected(
        self, agent_with_clash: _FakeAgent,
    ) -> None:
        blocks = await _invoke_tool(
            "hippo_contradictions_resolve",
            {"contradiction_id": ""},
        )
        payload = _payload(blocks)
        assert "error" in payload

    @pytest.mark.asyncio
    async def test_resolve_unknown_id_returns_error(
        self, agent_with_clash: _FakeAgent,
    ) -> None:
        blocks = await _invoke_tool(
            "hippo_contradictions_resolve",
            {"contradiction_id": "nonexistent_id"},
        )
        payload = _payload(blocks)
        assert "error" in payload

    @pytest.mark.asyncio
    async def test_double_resolve_is_rejected(
        self, agent_with_clash: _FakeAgent,
    ) -> None:
        await _invoke_tool("hippo_contradictions_scan", {})
        listing = _payload(
            await _invoke_tool("hippo_contradictions_list", {}),
        )
        cid = listing["items"][0]["id"]
        first = _payload(await _invoke_tool(
            "hippo_contradictions_resolve",
            {"contradiction_id": cid, "note": "first"},
        ))
        assert first["ok"] is True
        second = _payload(await _invoke_tool(
            "hippo_contradictions_resolve",
            {"contradiction_id": cid, "note": "second"},
        ))
        assert "error" in second
