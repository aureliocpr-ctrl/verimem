"""FORGIA pezzo #162 — MCP tool ``hippo_skill_bundles``.

Surfaces `memory.skill_bundle_candidates` over MCP so a client can
introspect natural skill bundles without coupling to the in-process
agent.
"""
from __future__ import annotations

import json
from typing import Any

import pytest

from verimem import mcp_server


class _FakeMemoryWithBundles:
    def skill_bundle_candidates(
        self, *, min_count: int = 3, min_overlap: float = 0.6,
    ) -> list[tuple[str, str, int]]:
        # Two pairs hardcoded for assertion. The second pair only
        # appears when min_count <= 2.
        out = [("A", "C", 5)]
        if min_count <= 2:
            out.append(("A", "B", 3))
        return out


class _FakeAgent:
    memory = _FakeMemoryWithBundles()


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
def fake_agent(monkeypatch: pytest.MonkeyPatch) -> _FakeAgent:
    a = _FakeAgent()
    monkeypatch.setattr(mcp_server, "_ag", lambda: a)
    return a


@pytest.mark.asyncio
async def test_hippo_skill_bundles_default_thresholds(
    fake_agent: _FakeAgent,
) -> None:
    blocks = await _invoke_tool("hippo_skill_bundles")
    payload = json.loads(blocks[0])
    # default min_count=3 → only ("A","C",5)
    assert payload == [{"a": "A", "b": "C", "count": 5}]


@pytest.mark.asyncio
async def test_hippo_skill_bundles_lowered_threshold(
    fake_agent: _FakeAgent,
) -> None:
    blocks = await _invoke_tool(
        "hippo_skill_bundles",
        {"min_count": 2, "min_overlap": 0.0},
    )
    payload = json.loads(blocks[0])
    assert payload == [
        {"a": "A", "b": "C", "count": 5},
        {"a": "A", "b": "B", "count": 3},
    ]


@pytest.mark.asyncio
async def test_hippo_skill_bundles_listed_in_tool_set(
    fake_agent: _FakeAgent,
) -> None:
    from mcp.types import ListToolsRequest, PaginatedRequestParams
    handler = mcp_server.server.request_handlers[ListToolsRequest]
    req = ListToolsRequest(method="tools/list", params=PaginatedRequestParams())
    result = await handler(req)
    payload = result.root if hasattr(result, "root") else result
    names = {tool.name for tool in payload.tools}
    assert "hippo_skill_bundles" in names
