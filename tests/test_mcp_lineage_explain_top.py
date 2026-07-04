"""FORGIA pezzo #198 — MCP tools Wave 4.

* ``hippo_skill_lineage``  — DAG of `parent_skills` ancestry for a skill.
* ``hippo_recall_explain`` — semantic recall + per-component score breakdown.
* ``hippo_skill_top``      — top-k skills sorted by fitness, recency, or
                              activity (configurable).
"""
from __future__ import annotations

import json
from typing import Any

import pytest

from engram import mcp_server

# ---------- Fakes ---------------------------------------------------------


class _FakeSkill:
    def __init__(
        self, sid: str, *, parents: list[str] | None = None,
        name: str | None = None, fitness_mean: float = 0.5,
        trials: int = 0, successes: int = 0,
        last_used_at: float = 0.0,
        status: str = "candidate", trigger: str = "",
        body: str = "",
    ) -> None:
        self.id = sid
        self.name = name or f"skill-{sid}"
        self.parent_skills = list(parents or [])
        self.fitness_mean = fitness_mean
        self.trials = trials
        self.successes = successes
        self.last_used_at = last_used_at
        self.status = status
        self.trigger = trigger
        self.body = body
        self.stage = "nrem"
        self.compiled_macro = None


class _FakeSkillsStoreLineage:
    def __init__(self) -> None:
        # Tree:
        #   root1
        #   ├── child1 (parents: [root1])
        #   │   └── grand1 (parents: [child1])
        #   └── child2 (parents: [root1, root2])
        #   root2
        self._skills = {
            "root1": _FakeSkill("root1", fitness_mean=0.9, trials=10,
                                  successes=9, last_used_at=2000.0),
            "root2": _FakeSkill("root2", fitness_mean=0.4, trials=2,
                                  successes=1, last_used_at=1500.0),
            "child1": _FakeSkill("child1", parents=["root1"],
                                   fitness_mean=0.7, trials=5,
                                   successes=4, last_used_at=2500.0),
            "child2": _FakeSkill("child2", parents=["root1", "root2"],
                                   fitness_mean=0.6, trials=3,
                                   successes=2, last_used_at=2400.0),
            "grand1": _FakeSkill("grand1", parents=["child1"],
                                   fitness_mean=0.8, trials=7,
                                   successes=6, last_used_at=3000.0),
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


class _FakeMemoryRecallExplain:
    def __init__(self) -> None:
        self.episodes = []
        for i in range(3):
            ep = type("FakeEp", (), {})()
            ep.id = f"ep{i}"
            ep.task_text = f"task {i}"
            ep.outcome = "success"
            ep.salience_score = 0.4 + 0.2 * i
            ep.access_count = i
            ep.last_accessed_at = 1000.0 + 100 * i
            ep.created_at = 1000.0 + 100 * i
            ep.tokens_used = 100
            ep.num_steps = 2
            ep.final_answer = f"answer-{i}"
            self.episodes.append(ep)

    def recall_explain(self, query: str, k: int = 3) -> list[dict]:
        # Return 3 episodes with deterministic breakdowns.
        out = []
        for i, ep in enumerate(self.episodes[:k]):
            out.append({
                "episode": ep,
                "score": 0.9 - 0.1 * i,
                "breakdown": {
                    "vector_similarity": 0.85 - 0.05 * i,
                    "salience_boost": ep.salience_score,
                    "context_tcm": 0.0,
                    "access_count_weight": float(ep.access_count) * 0.05,
                    "retention_strength": 0.95 - 0.1 * i,
                },
            })
        return out


class _FakeAgent:
    def __init__(self) -> None:
        self.skills = _FakeSkillsStoreLineage()
        self.memory = _FakeMemoryRecallExplain()


# ---------- Helpers -------------------------------------------------------


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
async def test_wave4_tools_listed(fake_agent: _FakeAgent) -> None:
    from mcp.types import ListToolsRequest, PaginatedRequestParams
    handler = mcp_server.server.request_handlers[ListToolsRequest]
    req = ListToolsRequest(method="tools/list", params=PaginatedRequestParams())
    result = await handler(req)
    payload = result.root if hasattr(result, "root") else result
    names = {tool.name for tool in payload.tools}
    for n in ("hippo_skill_lineage", "hippo_recall_explain",
              "hippo_skill_top"):
        assert n in names, f"missing tool: {n}"


# ---------- hippo_skill_lineage ----------------------------------------


@pytest.mark.asyncio
async def test_skill_lineage_root(fake_agent: _FakeAgent) -> None:
    """Root skill has no parents — lineage is just itself."""
    blocks = await _invoke_tool(
        "hippo_skill_lineage", {"skill_id": "root1"},
    )
    payload = json.loads(blocks[0])
    assert payload["skill_id"] == "root1"
    assert payload["ancestors"] == []
    assert payload["depth"] == 0


@pytest.mark.asyncio
async def test_skill_lineage_one_level(fake_agent: _FakeAgent) -> None:
    blocks = await _invoke_tool(
        "hippo_skill_lineage", {"skill_id": "child1"},
    )
    payload = json.loads(blocks[0])
    ancestor_ids = [a["id"] for a in payload["ancestors"]]
    assert ancestor_ids == ["root1"]
    assert payload["depth"] == 1


@pytest.mark.asyncio
async def test_skill_lineage_two_levels(fake_agent: _FakeAgent) -> None:
    """grand1 → child1 → root1 (depth 2)."""
    blocks = await _invoke_tool(
        "hippo_skill_lineage", {"skill_id": "grand1"},
    )
    payload = json.loads(blocks[0])
    ancestor_ids = {a["id"] for a in payload["ancestors"]}
    assert ancestor_ids == {"child1", "root1"}
    assert payload["depth"] == 2


@pytest.mark.asyncio
async def test_skill_lineage_diamond(fake_agent: _FakeAgent) -> None:
    """child2 has 2 parents (root1, root2) — deduped, both ancestors."""
    blocks = await _invoke_tool(
        "hippo_skill_lineage", {"skill_id": "child2"},
    )
    payload = json.loads(blocks[0])
    ancestor_ids = {a["id"] for a in payload["ancestors"]}
    assert ancestor_ids == {"root1", "root2"}
    assert payload["depth"] == 1


@pytest.mark.asyncio
async def test_skill_lineage_unknown_id(fake_agent: _FakeAgent) -> None:
    blocks = await _invoke_tool(
        "hippo_skill_lineage", {"skill_id": "ghost"},
    )
    payload = json.loads(blocks[0])
    assert "error" in payload


# ---------- hippo_recall_explain ----------------------------------------


@pytest.mark.asyncio
async def test_recall_explain_basic(fake_agent: _FakeAgent) -> None:
    blocks = await _invoke_tool(
        "hippo_recall_explain", {"query": "task", "k": 3},
    )
    payload = json.loads(blocks[0])
    assert "results" in payload
    assert len(payload["results"]) == 3
    first = payload["results"][0]
    assert "score" in first
    assert "breakdown" in first
    assert "vector_similarity" in first["breakdown"]
    assert "salience_boost" in first["breakdown"]
    assert "retention_strength" in first["breakdown"]


@pytest.mark.asyncio
async def test_recall_explain_default_k(fake_agent: _FakeAgent) -> None:
    blocks = await _invoke_tool(
        "hippo_recall_explain", {"query": "task"},
    )
    payload = json.loads(blocks[0])
    # default k=5 capped by available episodes (3)
    assert len(payload["results"]) == 3


# ---------- hippo_skill_top --------------------------------------------


@pytest.mark.asyncio
async def test_skill_top_by_fitness(fake_agent: _FakeAgent) -> None:
    blocks = await _invoke_tool(
        "hippo_skill_top", {"sort_by": "fitness", "k": 3},
    )
    payload = json.loads(blocks[0])
    assert payload["sort_by"] == "fitness"
    items = payload["items"]
    assert len(items) == 3
    # root1 has highest fitness 0.9
    assert items[0]["id"] == "root1"
    # all sorted descending
    fitnesses = [it["fitness_mean"] for it in items]
    assert fitnesses == sorted(fitnesses, reverse=True)


@pytest.mark.asyncio
async def test_skill_top_by_recency(fake_agent: _FakeAgent) -> None:
    blocks = await _invoke_tool(
        "hippo_skill_top", {"sort_by": "recency", "k": 2},
    )
    payload = json.loads(blocks[0])
    items = payload["items"]
    # grand1 has last_used_at=3000 (most recent)
    assert items[0]["id"] == "grand1"
    # newest first
    assert items[0]["last_used_at"] >= items[1]["last_used_at"]


@pytest.mark.asyncio
async def test_skill_top_by_activity(fake_agent: _FakeAgent) -> None:
    blocks = await _invoke_tool(
        "hippo_skill_top", {"sort_by": "activity", "k": 2},
    )
    payload = json.loads(blocks[0])
    items = payload["items"]
    # root1 has trials=10 (most)
    assert items[0]["id"] == "root1"


@pytest.mark.asyncio
async def test_skill_top_filter_status(fake_agent: _FakeAgent) -> None:
    # Mark root1 as promoted to test filter.
    fake_agent.skills._skills["root1"].status = "promoted"
    blocks = await _invoke_tool(
        "hippo_skill_top",
        {"sort_by": "fitness", "k": 5, "status": "promoted"},
    )
    payload = json.loads(blocks[0])
    items = payload["items"]
    assert len(items) == 1
    assert items[0]["id"] == "root1"


@pytest.mark.asyncio
async def test_skill_top_invalid_sort(fake_agent: _FakeAgent) -> None:
    blocks = await _invoke_tool(
        "hippo_skill_top", {"sort_by": "garbage"},
    )
    # MCP framework rejects the enum violation BEFORE the handler runs.
    # The error message is a plain string, not a JSON payload.
    assert any("garbage" in b or "validation error" in b.lower()
               for b in blocks)
