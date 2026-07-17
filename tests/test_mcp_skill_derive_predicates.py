"""FORGIA pezzo #213 — MCP tool `hippo_skill_derive_predicates`.

Wires the predicate-derivation heuristic to the MCP layer. Two modes:
  - dry-run (default): returns derived pre/post without writing.
  - apply=true: persists the derived pre/post on the Skill via the
    skills store's `store()`.

Idempotent: derived predicates are deterministic for the same
episode corpus + threshold.
"""
from __future__ import annotations

import json
from typing import Any

import pytest

from verimem import mcp_server
from verimem.skill import Skill

# ---------- Fakes --------------------------------------------------------


class _FakeEp:
    def __init__(self, eid: str, skills_used: list[str]) -> None:
        self.id = eid
        self.skills_used = skills_used


class _FakeMemory:
    def __init__(self, eps: list[_FakeEp]) -> None:
        self._eps = eps

    def all(self, limit: int | None = None) -> list[_FakeEp]:
        return list(self._eps if limit is None else self._eps[:limit])


class _FakeSkillsStore:
    def __init__(self, skills: list[Skill]) -> None:
        self._by_id = {s.id: s for s in skills}
        self.stored: list[Skill] = []

    def get(self, sid: str) -> Skill | None:
        return self._by_id.get(sid)

    def store(self, skill: Skill) -> None:
        self._by_id[skill.id] = skill
        self.stored.append(skill)


class _FakeAgent:
    def __init__(
        self, skills: list[Skill], episodes: list[_FakeEp],
    ) -> None:
        self.skills = _FakeSkillsStore(skills)
        self.memory = _FakeMemory(episodes)


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
        Skill(id="A", name="alpha", trigger="alpha"),
        Skill(id="B", name="beta", trigger="beta"),
        Skill(id="C", name="gamma", trigger="gamma"),
    ]
    eps = [
        _FakeEp("e1", ["A", "B", "C"]),
        _FakeEp("e2", ["A", "B", "C"]),
        _FakeEp("e3", ["A", "B"]),
    ]
    a = _FakeAgent(skills, eps)
    monkeypatch.setattr(mcp_server, "_ag", lambda: a)
    return a


# ---------- Tests --------------------------------------------------------


@pytest.mark.asyncio
async def test_listed(fake_agent: _FakeAgent) -> None:
    from mcp.types import ListToolsRequest, PaginatedRequestParams
    handler = mcp_server.server.request_handlers[ListToolsRequest]
    req = ListToolsRequest(method="tools/list", params=PaginatedRequestParams())
    result = await handler(req)
    payload = result.root if hasattr(result, "root") else result
    names = {tool.name for tool in payload.tools}
    assert "hippo_skill_derive_predicates" in names


@pytest.mark.asyncio
async def test_dry_run_returns_derived_predicates(
    fake_agent: _FakeAgent,
) -> None:
    """A→B in 100% of B occurrences → pre contains 'after_A'."""
    blocks = await _invoke_tool(
        "hippo_skill_derive_predicates",
        {"skill_id": "B"},
    )
    payload = json.loads(blocks[0])
    assert payload["skill_id"] == "B"
    assert payload["applied"] is False
    assert "after_A" in payload["preconditions"]
    assert payload["postconditions"] == ["after_B"]
    assert payload["n_episodes_used"] == 3


@pytest.mark.asyncio
async def test_apply_persists_predicates(fake_agent: _FakeAgent) -> None:
    """With apply=true, the skill is written back via store()."""
    blocks = await _invoke_tool(
        "hippo_skill_derive_predicates",
        {"skill_id": "B", "apply": True},
    )
    payload = json.loads(blocks[0])
    assert payload["applied"] is True
    # The skill in the store now has the derived predicates.
    updated = fake_agent.skills.get("B")
    assert updated is not None
    assert "after_A" in updated.preconditions
    assert "after_B" in updated.postconditions


@pytest.mark.asyncio
async def test_unknown_skill_id(fake_agent: _FakeAgent) -> None:
    blocks = await _invoke_tool(
        "hippo_skill_derive_predicates",
        {"skill_id": "NOT_EXISTS"},
    )
    payload = json.loads(blocks[0])
    assert payload["found"] is False


@pytest.mark.asyncio
async def test_threshold_respected(fake_agent: _FakeAgent) -> None:
    """High threshold → fewer predicates derived."""
    blocks_strict = await _invoke_tool(
        "hippo_skill_derive_predicates",
        {"skill_id": "B", "threshold": 0.99},
    )
    blocks_loose = await _invoke_tool(
        "hippo_skill_derive_predicates",
        {"skill_id": "B", "threshold": 0.1},
    )
    pl_strict = json.loads(blocks_strict[0])
    pl_loose = json.loads(blocks_loose[0])
    # Loose admits at least as many predicates as strict.
    assert len(pl_loose["preconditions"]) >= len(pl_strict["preconditions"])


@pytest.mark.asyncio
async def test_previous_state_returned_for_audit(
    fake_agent: _FakeAgent,
) -> None:
    """Output includes the skill's previous pre/post (for audit
    trail when applying)."""
    blocks = await _invoke_tool(
        "hippo_skill_derive_predicates",
        {"skill_id": "B"},
    )
    payload = json.loads(blocks[0])
    assert "previous_preconditions" in payload
    assert "previous_postconditions" in payload
    # Skill B started with no predicates → previous is empty.
    assert payload["previous_preconditions"] == []
    assert payload["previous_postconditions"] == []
