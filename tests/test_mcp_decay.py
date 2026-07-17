"""Cycle #110.C — MCP dispatch tests for hippo_decay_run.

Exercises the tool end-to-end with a real SemanticMemory so persistence
+ summary shape are validated together.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import pytest

from verimem import mcp_server
from verimem.semantic import Fact, SemanticMemory


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
def agent_with_aged_facts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> _FakeAgent:
    sm = SemanticMemory(db_path=tmp_path / "sm.db")
    now = time.time()
    SEC_DAY = 86400.0
    sm.store(Fact(id="fresh", proposition="recent claim", topic="t",
                   confidence=0.9, created_at=now - 0.001 * SEC_DAY))
    sm.store(Fact(id="medium", proposition="medium age claim", topic="t",
                   confidence=0.8, created_at=now - 30 * SEC_DAY))
    sm.store(Fact(id="ancient", proposition="ancient claim", topic="t",
                   confidence=0.9, created_at=now - 5_000 * SEC_DAY))
    agent = _FakeAgent(sm)
    monkeypatch.setattr(mcp_server, "_ag", lambda: agent)
    return agent


def _payload(blocks: list[str]) -> dict[str, Any]:
    return json.loads(blocks[0])


class TestDecayMCP:

    @pytest.mark.asyncio
    async def test_tool_listed(
        self, agent_with_aged_facts: _FakeAgent,
    ) -> None:
        from mcp.types import ListToolsRequest, PaginatedRequestParams
        handler = mcp_server.server.request_handlers[ListToolsRequest]
        result = await handler(ListToolsRequest(
            method="tools/list", params=PaginatedRequestParams(),
        ))
        payload = result.root if hasattr(result, "root") else result
        names = {tool.name for tool in payload.tools}
        assert "hippo_decay_run" in names

    @pytest.mark.asyncio
    async def test_default_run_persists_and_returns_summary(
        self, agent_with_aged_facts: _FakeAgent,
    ) -> None:
        blocks = await _invoke_tool("hippo_decay_run", {})
        payload = _payload(blocks)
        assert payload["facts_seen"] == 3
        assert payload["facts_updated"] >= 2  # medium + ancient
        assert payload["avg_confidence_after"] < payload["avg_confidence_before"]
        assert payload["dry_run"] is False
        # Persisted: ancient must have decayed
        ancient = agent_with_aged_facts.semantic.get("ancient")
        assert ancient.confidence < 0.9

    @pytest.mark.asyncio
    async def test_dry_run_does_not_persist(
        self, agent_with_aged_facts: _FakeAgent,
    ) -> None:
        before = agent_with_aged_facts.semantic.get("ancient").confidence
        blocks = await _invoke_tool("hippo_decay_run", {"dry_run": True})
        payload = _payload(blocks)
        assert payload["dry_run"] is True
        # Live DB row unchanged
        after = agent_with_aged_facts.semantic.get("ancient").confidence
        assert after == pytest.approx(before, abs=1e-9)

    @pytest.mark.asyncio
    async def test_floor_param_clamps_old_facts(
        self, agent_with_aged_facts: _FakeAgent,
    ) -> None:
        await _invoke_tool(
            "hippo_decay_run", {"tau_days": 10, "floor": 0.2},
        )
        ancient = agent_with_aged_facts.semantic.get("ancient")
        assert ancient.confidence == pytest.approx(0.2, abs=1e-6)

    @pytest.mark.asyncio
    async def test_tau_days_echoed_in_summary(
        self, agent_with_aged_facts: _FakeAgent,
    ) -> None:
        blocks = await _invoke_tool(
            "hippo_decay_run", {"tau_days": 14},
        )
        payload = _payload(blocks)
        assert payload["tau_days"] == 14.0
