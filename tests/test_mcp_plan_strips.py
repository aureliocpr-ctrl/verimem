"""FORGIA pezzo #209 — MCP tool `hippo_plan_strips`.

Wires Pezzo A (STRIPS planner over skill pre/post) to the MCP layer
so Claude Code can ask: "given these initial predicates and this
goal, what skill chain reaches the goal?" — symbolic chaining,
zero LLM, ms-scale.
"""
from __future__ import annotations

import json
from typing import Any

import pytest

from engram import mcp_server
from engram.skill import Skill

# ---------- Fakes --------------------------------------------------------


class _FakeSkillsStore:
    def __init__(self, skills: list[Skill]) -> None:
        self._skills = skills

    def all(self, status: str | None = None) -> list[Skill]:
        if status is None:
            return list(self._skills)
        return [s for s in self._skills if s.status == status]


class _FakeAgent:
    def __init__(self, skills: list[Skill]) -> None:
        self.skills = _FakeSkillsStore(skills)


# ---------- Helpers ------------------------------------------------------


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
    skills = [
        Skill(id="auth", name="authenticate", status="promoted",
              preconditions=["have_creds"],
              postconditions=["logged_in"]),
        Skill(id="fetch", name="fetch_data", status="promoted",
              preconditions=["logged_in"],
              postconditions=["data_loaded"]),
        Skill(id="render", name="render_view", status="promoted",
              preconditions=["data_loaded"],
              postconditions=["ui_rendered"]),
        Skill(id="weak", name="experimental", status="candidate",
              preconditions=["have_creds"],
              postconditions=["ui_rendered"]),  # 1-step shortcut
    ]
    a = _FakeAgent(skills)
    monkeypatch.setattr(mcp_server, "_ag", lambda: a)
    return a


# ---------- Tests --------------------------------------------------------


@pytest.mark.asyncio
async def test_plan_strips_listed(fake_agent: _FakeAgent) -> None:
    from mcp.types import ListToolsRequest, PaginatedRequestParams
    handler = mcp_server.server.request_handlers[ListToolsRequest]
    req = ListToolsRequest(method="tools/list", params=PaginatedRequestParams())
    result = await handler(req)
    payload = result.root if hasattr(result, "root") else result
    names = {tool.name for tool in payload.tools}
    assert "hippo_plan_strips" in names


@pytest.mark.asyncio
async def test_plan_strips_finds_chain(fake_agent: _FakeAgent) -> None:
    """Goal=ui_rendered, initial=have_creds → should find a plan."""
    blocks = await _invoke_tool(
        "hippo_plan_strips",
        {
            "initial_state": ["have_creds"],
            "goal_state": ["ui_rendered"],
        },
    )
    payload = json.loads(blocks[0])
    assert payload["found"] is True
    assert payload["n_steps"] >= 1
    # Plan must be a list of skill descriptors.
    assert isinstance(payload["plan"], list)
    for step in payload["plan"]:
        assert "id" in step and "name" in step


@pytest.mark.asyncio
async def test_plan_strips_already_satisfied(fake_agent: _FakeAgent) -> None:
    """Goal already in initial → empty plan, found=True."""
    blocks = await _invoke_tool(
        "hippo_plan_strips",
        {
            "initial_state": ["already"],
            "goal_state": ["already"],
        },
    )
    payload = json.loads(blocks[0])
    assert payload["found"] is True
    assert payload["n_steps"] == 0
    assert payload["plan"] == []


@pytest.mark.asyncio
async def test_plan_strips_no_solution(fake_agent: _FakeAgent) -> None:
    """No skills bridge initial→goal."""
    blocks = await _invoke_tool(
        "hippo_plan_strips",
        {
            "initial_state": ["unrelated"],
            "goal_state": ["ui_rendered"],
        },
    )
    payload = json.loads(blocks[0])
    assert payload["found"] is False
    assert payload["plan"] == []


@pytest.mark.asyncio
async def test_plan_strips_status_filter(fake_agent: _FakeAgent) -> None:
    """`status=promoted` excludes the candidate shortcut, forcing
    the 3-step chain instead of the 1-step experimental skill."""
    blocks = await _invoke_tool(
        "hippo_plan_strips",
        {
            "initial_state": ["have_creds"],
            "goal_state": ["ui_rendered"],
            "status": "promoted",
        },
    )
    payload = json.loads(blocks[0])
    assert payload["found"] is True
    # 3 promoted skills required: auth → fetch → render.
    assert payload["n_steps"] == 3
    assert [s["id"] for s in payload["plan"]] == ["auth", "fetch", "render"]


@pytest.mark.asyncio
async def test_plan_strips_default_includes_candidates(
    fake_agent: _FakeAgent,
) -> None:
    """No status filter → all skills considered, including the
    candidate shortcut (which is shorter)."""
    blocks = await _invoke_tool(
        "hippo_plan_strips",
        {
            "initial_state": ["have_creds"],
            "goal_state": ["ui_rendered"],
        },
    )
    payload = json.loads(blocks[0])
    assert payload["found"] is True
    # Candidate shortcut (id=weak) is 1 step and should win.
    assert payload["n_steps"] == 1
    assert payload["plan"][0]["id"] == "weak"


@pytest.mark.asyncio
async def test_plan_strips_max_depth(fake_agent: _FakeAgent) -> None:
    """max_depth=2 cannot reach a 3-step chain when only `promoted`
    skills are considered."""
    blocks = await _invoke_tool(
        "hippo_plan_strips",
        {
            "initial_state": ["have_creds"],
            "goal_state": ["ui_rendered"],
            "status": "promoted",
            "max_depth": 2,
        },
    )
    payload = json.loads(blocks[0])
    assert payload["found"] is False
