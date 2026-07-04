"""FORGIA pezzo #168 — MCP tool ``hippo_compound_skills``."""
from __future__ import annotations

import json
from typing import Any

import pytest

from engram import mcp_server


class _FakeSkill:
    def __init__(self, sid, name, parents):
        self.id = sid
        self.name = name
        self.parent_skills = parents
        self.trigger = "t"
        self.body = "b"
        self.fitness_mean = 0.7
        self.status = "candidate"
        self.stage = "nrem"
        self.trials = 2
        self.successes = 1


class _FakeSkills:
    def __init__(self):
        self._sk = [
            _FakeSkill("leaf", "leaf-skill", []),
            _FakeSkill("compound", "a_then_b", ["a", "b"]),
        ]

    def all(self, status=None):
        return list(self._sk)


class _FakeMemoryStub:
    def skill_bundle_candidates(self, **_):
        return []


class _FakeAgent:
    skills = _FakeSkills()
    memory = _FakeMemoryStub()
    semantic = None

    @property
    def wake(self):
        # The MCP tool delegates via wake.compound_skills(); we mimic.
        outer = self

        class _W:
            def compound_skills(self_inner):
                return [s for s in outer.skills.all() if len(s.parent_skills) >= 2]

        return _W()


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
async def test_hippo_compound_skills_returns_only_compound(
    fake_agent: _FakeAgent,
) -> None:
    blocks = await _invoke_tool("hippo_compound_skills")
    payload = json.loads(blocks[0])
    assert isinstance(payload, list)
    assert len(payload) == 1
    assert payload[0]["id"] == "compound"
    assert payload[0]["name"] == "a_then_b"
    assert payload[0]["parent_skills"] == ["a", "b"]


@pytest.mark.asyncio
async def test_hippo_compound_skills_listed(fake_agent: _FakeAgent) -> None:
    from mcp.types import ListToolsRequest, PaginatedRequestParams
    handler = mcp_server.server.request_handlers[ListToolsRequest]
    req = ListToolsRequest(method="tools/list", params=PaginatedRequestParams())
    result = await handler(req)
    payload = result.root if hasattr(result, "root") else result
    names = {tool.name for tool in payload.tools}
    assert "hippo_compound_skills" in names
