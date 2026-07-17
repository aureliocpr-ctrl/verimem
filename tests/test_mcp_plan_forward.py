"""FORGIA pezzo #208 — MCP tool `hippo_plan_forward`.

Wires Pezzo B (forward planning, hippocampal forward sweeps Pfeiffer
& Foster 2013) to the MCP layer so Claude Code can ask: "given I'm
about to use skill X, what are the most likely 3-step trajectories?"
WITHOUT calling an LLM.

Pure local computation:
  1. Pull skill_used sequences from the last N episodes.
  2. Build the empirical transition matrix P.
  3. Beam-search from `start_skill` for top `beam_width` paths of
     up to `depth` steps. Optionally stop at `goal_skill`.

Returns: `{start_skill, depth, beam_width, n_episodes_used,
n_unique_skills, plans}` where each plan is `{path, log_prob, prob}`.
"""
from __future__ import annotations

import json
from typing import Any

import pytest

from verimem import mcp_server

# ---------- Fakes --------------------------------------------------------


class _FakeEpisode:
    def __init__(self, eid: str, skills_used: list[str]) -> None:
        self.id = eid
        self.skills_used = skills_used


class _FakeMemoryStore:
    def __init__(self, episodes: list[_FakeEpisode]) -> None:
        self._episodes = episodes

    def all(self, limit: int | None = None) -> list[_FakeEpisode]:
        if limit is None:
            return list(self._episodes)
        return self._episodes[:limit]


class _FakeAgent:
    def __init__(self, episodes: list[_FakeEpisode]) -> None:
        self.memory = _FakeMemoryStore(episodes)


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
    # Toy corpus: A→B→C is the most-likely chain (3 episodes), with
    # one A→D→D side branch.
    eps = [
        _FakeEpisode("e1", ["A", "B", "C"]),
        _FakeEpisode("e2", ["A", "B", "C"]),
        _FakeEpisode("e3", ["A", "B", "C"]),
        _FakeEpisode("e4", ["A", "D", "D"]),
        _FakeEpisode("e5", ["B", "C"]),
    ]
    a = _FakeAgent(eps)
    monkeypatch.setattr(mcp_server, "_ag", lambda: a)
    return a


# ---------- Tests --------------------------------------------------------


@pytest.mark.asyncio
async def test_plan_forward_listed(fake_agent: _FakeAgent) -> None:
    """The MCP server registers `hippo_plan_forward`."""
    from mcp.types import ListToolsRequest, PaginatedRequestParams
    handler = mcp_server.server.request_handlers[ListToolsRequest]
    req = ListToolsRequest(method="tools/list", params=PaginatedRequestParams())
    result = await handler(req)
    payload = result.root if hasattr(result, "root") else result
    names = {tool.name for tool in payload.tools}
    assert "hippo_plan_forward" in names


@pytest.mark.asyncio
async def test_plan_forward_basic(fake_agent: _FakeAgent) -> None:
    """A known start_skill returns plans with path/log_prob/prob."""
    blocks = await _invoke_tool(
        "hippo_plan_forward", {"start_skill": "A", "depth": 2,
                                  "beam_width": 3},
    )
    payload = json.loads(blocks[0])
    assert payload["start_skill"] == "A"
    assert payload["depth"] == 2
    assert payload["n_episodes_used"] >= 4
    assert payload["plans"], "expected at least one plan"
    top = payload["plans"][0]
    assert "path" in top and "log_prob" in top and "prob" in top
    assert top["path"][0] == "A"
    # Top plan should reach C (A→B→C is dominant).
    assert top["path"][-1] == "C", (
        f"top path should end at C; got {top['path']}"
    )


@pytest.mark.asyncio
async def test_plan_forward_unknown_start(fake_agent: _FakeAgent) -> None:
    """Unknown start_skill returns empty plans, no crash."""
    blocks = await _invoke_tool(
        "hippo_plan_forward", {"start_skill": "ZZZ", "depth": 2},
    )
    payload = json.loads(blocks[0])
    assert payload["plans"] == []
    assert payload["start_skill"] == "ZZZ"


@pytest.mark.asyncio
async def test_plan_forward_respects_beam_width(
    fake_agent: _FakeAgent,
) -> None:
    """At most beam_width active beams (frozen-by-goal can exceed)."""
    blocks = await _invoke_tool(
        "hippo_plan_forward", {"start_skill": "A", "depth": 2,
                                  "beam_width": 1},
    )
    payload = json.loads(blocks[0])
    # No goal → only beams (no frozen). beam_width=1 → exactly 1 plan.
    assert len(payload["plans"]) == 1


@pytest.mark.asyncio
async def test_plan_forward_with_goal_skill(fake_agent: _FakeAgent) -> None:
    """`goal_skill="C"` should yield at least one plan ending at C."""
    blocks = await _invoke_tool(
        "hippo_plan_forward", {"start_skill": "A", "depth": 4,
                                  "beam_width": 3, "goal_skill": "C"},
    )
    payload = json.loads(blocks[0])
    assert payload["plans"], "expected at least one plan"
    assert any(p["path"][-1] == "C" for p in payload["plans"])


@pytest.mark.asyncio
async def test_plan_forward_descending_log_prob(
    fake_agent: _FakeAgent,
) -> None:
    """Plans returned in descending log_prob order."""
    blocks = await _invoke_tool(
        "hippo_plan_forward", {"start_skill": "A", "depth": 2,
                                  "beam_width": 5},
    )
    payload = json.loads(blocks[0])
    log_probs = [p["log_prob"] for p in payload["plans"]]
    assert log_probs == sorted(log_probs, reverse=True)


@pytest.mark.asyncio
async def test_plan_forward_empty_memory(monkeypatch) -> None:
    """No episodes → empty plans, n_episodes_used=0."""
    monkeypatch.setattr(mcp_server, "_ag", lambda: _FakeAgent([]))
    blocks = await _invoke_tool(
        "hippo_plan_forward", {"start_skill": "A", "depth": 2},
    )
    payload = json.loads(blocks[0])
    assert payload["plans"] == []
    assert payload["n_episodes_used"] == 0


@pytest.mark.asyncio
async def test_plan_forward_n_unique_skills(fake_agent: _FakeAgent) -> None:
    """Result reports n_unique_skills derived from the corpus."""
    blocks = await _invoke_tool(
        "hippo_plan_forward", {"start_skill": "A", "depth": 1},
    )
    payload = json.loads(blocks[0])
    # Skills in fake corpus: A, B, C, D = 4 unique.
    assert payload["n_unique_skills"] == 4
