"""FORGIA pezzo #172 — MCP tool ``hippo_skill_antagonists``.

Surfaces lateral-inhibition links (skills with antagonists set)
over MCP for client-side audit / dashboard visualization.
"""
from __future__ import annotations

import json
from typing import Any

import pytest

from verimem import mcp_server


class _Skill:
    def __init__(self, sid, name, antagonists):
        self.id = sid
        self.name = name
        self.antagonists = list(antagonists)
        self.trigger = "t"
        self.body = "b"


class _Skills:
    def __init__(self):
        self._sk = [
            _Skill("A", "alpha", ["B"]),
            _Skill("B", "beta", ["A"]),
            _Skill("C", "gamma", []),  # no antagonists
        ]

    def all(self, status=None):
        return list(self._sk)


class _Agent:
    skills = _Skills()


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
def fake_agent(monkeypatch: pytest.MonkeyPatch) -> _Agent:
    a = _Agent()
    monkeypatch.setattr(mcp_server, "_ag", lambda: a)
    return a


@pytest.mark.asyncio
async def test_skill_antagonists_returns_pairs(fake_agent: _Agent):
    blocks = await _invoke_tool("hippo_skill_antagonists")
    payload = json.loads(blocks[0])
    # C has no antagonists → excluded.
    assert isinstance(payload, list)
    ids = {item["id"] for item in payload}
    assert ids == {"A", "B"}
    a = next(item for item in payload if item["id"] == "A")
    assert a["antagonists"] == ["B"]


@pytest.mark.asyncio
async def test_skill_antagonists_listed(fake_agent: _Agent):
    from mcp.types import ListToolsRequest, PaginatedRequestParams
    handler = mcp_server.server.request_handlers[ListToolsRequest]
    req = ListToolsRequest(
        method="tools/list", params=PaginatedRequestParams(),
    )
    result = await handler(req)
    payload = result.root if hasattr(result, "root") else result
    names = {tool.name for tool in payload.tools}
    assert "hippo_skill_antagonists" in names
