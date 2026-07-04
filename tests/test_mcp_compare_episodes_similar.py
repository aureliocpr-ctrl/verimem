"""FORGIA pezzo #199 — MCP tools Wave 5.

* ``hippo_skill_compare``    — diff between two skills (body/trigger/fitness).
* ``hippo_episodes_by_skill`` — every episode that used a given skill.
* ``hippo_skill_similar``    — top-k skills with the most overlap (Jaccard
                                on body tokens) to a given skill.
"""
from __future__ import annotations

import json
from typing import Any

import pytest

from engram import mcp_server

# ---------- Fakes ---------------------------------------------------------


class _FakeSkill:
    def __init__(self, sid: str, *, name: str, body: str = "",
                  trigger: str = "", fitness_mean: float = 0.5,
                  trials: int = 0, successes: int = 0,
                  status: str = "candidate", version: int = 1) -> None:
        self.id = sid
        self.name = name
        self.body = body
        self.trigger = trigger
        self.fitness_mean = fitness_mean
        self.trials = trials
        self.successes = successes
        self.status = status
        self.version = version
        self.parent_skills: list[str] = []
        self.compiled_macro = None


class _FakeSkillsStore:
    def __init__(self) -> None:
        self._skills = {
            "s_a": _FakeSkill(
                "s_a", name="parse JSON",
                body="open file, json.load, return dict",
                trigger="when parsing JSON",
                fitness_mean=0.85, trials=10, successes=9,
                status="promoted",
            ),
            "s_b": _FakeSkill(
                "s_b", name="parse JSON v2",
                body="open file, json.load, validate schema, return dict",
                trigger="when parsing JSON with validation",
                fitness_mean=0.75, trials=4, successes=3,
                status="candidate",
            ),
            "s_c": _FakeSkill(
                "s_c", name="parse YAML",
                body="open file, yaml.safe_load, return dict",
                trigger="when parsing YAML",
                fitness_mean=0.65, trials=3, successes=2,
                status="candidate",
            ),
            "s_d": _FakeSkill(
                "s_d", name="send email",
                body="connect smtp, send message",
                trigger="when sending email",
                fitness_mean=0.50, trials=5, successes=2,
                status="candidate",
            ),
        }

    def get(self, sid: str) -> _FakeSkill | None:
        return self._skills.get(sid)

    def all(self, status: str | None = None) -> list[_FakeSkill]:
        items = list(self._skills.values())
        if status:
            items = [s for s in items if s.status == status]
        return items

    def count(self, status: str | None = None) -> int:
        return len(self.all(status=status))


class _FakeMemoryEpisodesBySkill:
    def __init__(self) -> None:
        self.episodes = []
        # Episodes referencing skills.
        for i, sk_used in enumerate([
            ["s_a"], ["s_a", "s_c"], ["s_b"], [], ["s_a"],
        ]):
            ep = type("FakeEp", (), {})()
            ep.id = f"ep{i}"
            ep.task_id = f"task-{i}"
            ep.task_text = f"task {i}"
            ep.outcome = "success" if i % 2 == 0 else "failure"
            ep.tokens_used = 100 * (i + 1)
            ep.num_steps = 2
            ep.created_at = 1000.0 + 100 * i
            ep.skills_used = list(sk_used)
            ep.final_answer = f"answer {i}"
            self.episodes.append(ep)

    def all(self, limit: int | None = None) -> list:
        eps = sorted(self.episodes, key=lambda e: e.created_at, reverse=True)
        return eps[:limit] if limit else eps


class _FakeAgent:
    def __init__(self) -> None:
        self.skills = _FakeSkillsStore()
        self.memory = _FakeMemoryEpisodesBySkill()


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
    a = _FakeAgent()
    monkeypatch.setattr(mcp_server, "_ag", lambda: a)
    return a


# ---------- listing -----------------------------------------------------


@pytest.mark.asyncio
async def test_wave5_tools_listed(fake_agent: _FakeAgent) -> None:
    from mcp.types import ListToolsRequest, PaginatedRequestParams
    handler = mcp_server.server.request_handlers[ListToolsRequest]
    req = ListToolsRequest(method="tools/list", params=PaginatedRequestParams())
    result = await handler(req)
    payload = result.root if hasattr(result, "root") else result
    names = {tool.name for tool in payload.tools}
    for n in ("hippo_skill_compare", "hippo_episodes_by_skill",
              "hippo_skill_similar"):
        assert n in names, f"missing tool: {n}"


# ---------- hippo_skill_compare ------------------------------------------


@pytest.mark.asyncio
async def test_skill_compare_two_versions(fake_agent: _FakeAgent) -> None:
    blocks = await _invoke_tool(
        "hippo_skill_compare", {"skill_a": "s_a", "skill_b": "s_b"},
    )
    payload = json.loads(blocks[0])
    assert payload["skill_a"]["id"] == "s_a"
    assert payload["skill_b"]["id"] == "s_b"
    # Body diff captures the new "validate schema" tokens.
    assert "body_diff" in payload
    assert "fitness_delta" in payload  # b - a → 0.75 - 0.85 = -0.10
    assert payload["fitness_delta"] == pytest.approx(-0.10, abs=1e-6)
    assert payload["trials_delta"] == -6  # 4 - 10
    assert "name_changed" in payload
    assert payload["name_changed"] is True


@pytest.mark.asyncio
async def test_skill_compare_self(fake_agent: _FakeAgent) -> None:
    blocks = await _invoke_tool(
        "hippo_skill_compare", {"skill_a": "s_a", "skill_b": "s_a"},
    )
    payload = json.loads(blocks[0])
    assert payload["fitness_delta"] == 0.0
    assert payload["body_changed"] is False
    assert payload["name_changed"] is False


@pytest.mark.asyncio
async def test_skill_compare_unknown(fake_agent: _FakeAgent) -> None:
    blocks = await _invoke_tool(
        "hippo_skill_compare", {"skill_a": "ghost", "skill_b": "s_a"},
    )
    payload = json.loads(blocks[0])
    assert "error" in payload


# ---------- hippo_episodes_by_skill --------------------------------------


@pytest.mark.asyncio
async def test_episodes_by_skill_basic(fake_agent: _FakeAgent) -> None:
    blocks = await _invoke_tool(
        "hippo_episodes_by_skill", {"skill_id": "s_a"},
    )
    payload = json.loads(blocks[0])
    # ep0, ep1, ep4 used s_a → 3 episodes
    assert payload["skill_id"] == "s_a"
    assert payload["count"] == 3
    ids = {it["id"] for it in payload["items"]}
    assert ids == {"ep0", "ep1", "ep4"}


@pytest.mark.asyncio
async def test_episodes_by_skill_outcome_filter(fake_agent: _FakeAgent) -> None:
    blocks = await _invoke_tool(
        "hippo_episodes_by_skill",
        {"skill_id": "s_a", "outcome": "failure"},
    )
    payload = json.loads(blocks[0])
    # ep0=success, ep1=failure, ep4=success → outcome=failure → ep1 only
    assert payload["count"] == 1
    assert payload["items"][0]["id"] == "ep1"


@pytest.mark.asyncio
async def test_episodes_by_skill_unused(fake_agent: _FakeAgent) -> None:
    blocks = await _invoke_tool(
        "hippo_episodes_by_skill", {"skill_id": "ghost"},
    )
    payload = json.loads(blocks[0])
    assert payload["count"] == 0
    assert payload["items"] == []


# ---------- hippo_skill_similar -----------------------------------------


@pytest.mark.asyncio
async def test_skill_similar_finds_overlap(fake_agent: _FakeAgent) -> None:
    """s_a body shares many tokens with s_b and s_c."""
    blocks = await _invoke_tool(
        "hippo_skill_similar", {"skill_id": "s_a", "k": 3},
    )
    payload = json.loads(blocks[0])
    assert payload["skill_id"] == "s_a"
    assert "items" in payload
    items = payload["items"]
    assert len(items) <= 3
    # s_b should be the most similar (parse JSON v2).
    assert items[0]["id"] == "s_b"
    # s_d (send email) should NOT be in top-2.
    top2_ids = {it["id"] for it in items[:2]}
    assert "s_d" not in top2_ids
    # All items must include similarity score.
    for it in items:
        assert "jaccard" in it
        assert 0.0 <= it["jaccard"] <= 1.0


@pytest.mark.asyncio
async def test_skill_similar_unknown_id(fake_agent: _FakeAgent) -> None:
    blocks = await _invoke_tool(
        "hippo_skill_similar", {"skill_id": "ghost"},
    )
    payload = json.loads(blocks[0])
    assert "error" in payload


@pytest.mark.asyncio
async def test_skill_similar_excludes_self(fake_agent: _FakeAgent) -> None:
    blocks = await _invoke_tool(
        "hippo_skill_similar", {"skill_id": "s_a", "k": 5},
    )
    payload = json.loads(blocks[0])
    ids = [it["id"] for it in payload["items"]]
    assert "s_a" not in ids
