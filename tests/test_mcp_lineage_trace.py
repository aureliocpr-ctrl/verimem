"""Cycle #52 — hippo_lineage_trace walker over the unified graph.

Walks edges:
- episode ↔ episode  (via causal_edges → memory.causal_graph())
- episode ↔ fact     (via facts.source_episodes — Python-side filter)
- episode ↔ skill    (via episode.skills_used)
- skill   ↔ skill    (via skill_lineage → skills.lineage_graph())

Direction:
- 'forward':  outgoing edges (downstream)
- 'backward': incoming edges (upstream)
- 'both':     follow both directions

Safety:
- max_depth caps BFS depth (default 3)
- max_nodes caps result size with `truncated: True` flag (default 200)

These tests use fakes that mirror the REAL API surface of EpisodicMemory,
SkillLibrary and SemanticMemory (causal_graph, lineage_graph, all, get).
This means a green test here = the walker will run unmodified against
the real classes in production.
"""
from __future__ import annotations

import json
import time
from typing import Any

import networkx as nx
import pytest

from verimem import mcp_server

# ---------- Fakes mirroring real API ------------------------------------


class _FakeFact:
    def __init__(self, fid: str, *, proposition: str, topic: str = "",
                 source_episodes: list[str] | None = None) -> None:
        self.id = fid
        self.proposition = proposition
        self.topic = topic
        self.confidence = 0.9
        self.source_episodes = source_episodes or []
        self.created_at = time.time()


class _FakeEpisode:
    def __init__(self, eid: str, *, task: str = "",
                 skills_used: list[str] | None = None) -> None:
        self.id = eid
        self.task_id = f"t-{eid}"
        self.task_text = task
        self.outcome = "success"
        self.final_answer = "ok"
        self.skills_used = skills_used or []
        self.tokens_used = 0
        self.num_steps = 1
        self.created_at = time.time()
        self.notes = ""
        self.critique = ""


class _FakeSkill:
    def __init__(self, sid: str, *, name: str = "") -> None:
        self.id = sid
        self.name = name or f"skill-{sid}"
        self.status = "promoted"
        self.stage = "active"
        self.fitness_mean = 0.7


class _FakeSemantic:
    def __init__(self, facts: list[_FakeFact] | None = None) -> None:
        self._facts = {f.id: f for f in (facts or [])}

    def get(self, fid: str) -> _FakeFact | None:
        return self._facts.get(fid)

    def all(self) -> list[_FakeFact]:
        return list(self._facts.values())


class _FakeMemory:
    def __init__(self, episodes: list[_FakeEpisode] | None = None,
                 edges: list[tuple[str, str, str, float]] | None = None) -> None:
        self._episodes = {e.id: e for e in (episodes or [])}
        # edges: (src, dst, via_skill, weight)
        self._edges = list(edges or [])

    def get(self, eid: str) -> _FakeEpisode | None:
        return self._episodes.get(eid)

    def all(self) -> list[_FakeEpisode]:
        return list(self._episodes.values())

    def causal_graph(self) -> nx.DiGraph:
        g = nx.DiGraph()
        for e in self._episodes.values():
            g.add_node(e.id)
        for src, dst, skill, weight in self._edges:
            g.add_edge(src, dst, skill=skill, weight=weight)
        return g


class _FakeSkillsStore:
    def __init__(self, skills: list[_FakeSkill] | None = None,
                 lineage: list[tuple[str, str, str]] | None = None) -> None:
        # lineage: (parent_id, child_id, relation)
        self._skills = {s.id: s for s in (skills or [])}
        self._lineage = list(lineage or [])

    def get(self, sid: str) -> _FakeSkill | None:
        return self._skills.get(sid)

    def all(self, status=None) -> list[_FakeSkill]:
        items = list(self._skills.values())
        if status:
            items = [s for s in items if s.status == status]
        return items

    def lineage_graph(self) -> nx.DiGraph:
        g = nx.DiGraph()
        for s in self._skills.values():
            g.add_node(s.id, name=s.name, status=s.status,
                       stage=s.stage, fitness=s.fitness_mean)
        for parent, child, relation in self._lineage:
            g.add_edge(parent, child, relation=relation)
        return g


class _FakeAgent:
    def __init__(self, memory, semantic, skills) -> None:
        self.memory = memory
        self.semantic = semantic
        self.skills = skills


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


# ---------- Scenario fixture --------------------------------------------


@pytest.fixture
def small_graph(monkeypatch: pytest.MonkeyPatch) -> _FakeAgent:
    """Minimal scenario:
        ep1 --causal--> ep2 --causal--> ep3
        ep1 has fact f1 (source_episodes=[ep1])
        ep2 has fact f2 (source_episodes=[ep2])
        ep1.skills_used = [sk_a]
        sk_a --lineage(derived_from)--> sk_b
    """
    ep1 = _FakeEpisode("ep1", task="root task", skills_used=["sk_a"])
    ep2 = _FakeEpisode("ep2", task="follow up")
    ep3 = _FakeEpisode("ep3", task="final step")
    sk_a = _FakeSkill("sk_a", name="root_skill")
    sk_b = _FakeSkill("sk_b", name="derived_skill")
    f1 = _FakeFact("f1", proposition="atom from ep1",
                   source_episodes=["ep1"])
    f2 = _FakeFact("f2", proposition="atom from ep2",
                   source_episodes=["ep2"])
    mem = _FakeMemory(
        episodes=[ep1, ep2, ep3],
        edges=[
            ("ep1", "ep2", "narrative_link", 1.0),
            ("ep2", "ep3", "narrative_link", 1.0),
        ],
    )
    sem = _FakeSemantic(facts=[f1, f2])
    skills = _FakeSkillsStore(
        skills=[sk_a, sk_b],
        lineage=[("sk_a", "sk_b", "derived_from")],
    )
    a = _FakeAgent(mem, sem, skills)
    monkeypatch.setattr(mcp_server, "_ag", lambda: a)
    return a


# ---------- Tests --------------------------------------------------------


@pytest.mark.asyncio
async def test_lineage_trace_from_episode_forward(small_graph) -> None:
    """Forward from ep1: reaches ep2, ep3 (causal), f1 (has_fact),
    sk_a (used_skill), sk_b (lineage child of sk_a) within depth 3."""
    blocks = await _invoke_tool(
        "hippo_lineage_trace",
        {"start_id": "ep1", "kind": "episode",
         "direction": "forward", "max_depth": 3},
    )
    payload = json.loads(blocks[0])
    assert payload["ok"] is True
    node_ids = {(n["id"], n["kind"]) for n in payload["nodes"]}
    assert ("ep1", "episode") in node_ids
    assert ("ep2", "episode") in node_ids
    assert ("ep3", "episode") in node_ids
    assert ("f1", "fact") in node_ids
    assert ("sk_a", "skill") in node_ids
    assert ("sk_b", "skill") in node_ids
    # f2 must be reachable: ep1 -> ep2 -> f2 (depth 2)
    assert ("f2", "fact") in node_ids


@pytest.mark.asyncio
async def test_lineage_trace_from_fact_backward(small_graph) -> None:
    """Backward from f1: reaches its source ep1."""
    blocks = await _invoke_tool(
        "hippo_lineage_trace",
        {"start_id": "f1", "kind": "fact",
         "direction": "backward", "max_depth": 2},
    )
    payload = json.loads(blocks[0])
    assert payload["ok"] is True
    node_ids = {(n["id"], n["kind"]) for n in payload["nodes"]}
    assert ("f1", "fact") in node_ids
    assert ("ep1", "episode") in node_ids


@pytest.mark.asyncio
async def test_lineage_trace_max_depth_cap(small_graph) -> None:
    """max_depth=1 limits BFS to direct neighbors only."""
    blocks = await _invoke_tool(
        "hippo_lineage_trace",
        {"start_id": "ep1", "kind": "episode",
         "direction": "forward", "max_depth": 1},
    )
    payload = json.loads(blocks[0])
    node_ids = {(n["id"], n["kind"]) for n in payload["nodes"]}
    # Depth 0: ep1 itself
    # Depth 1: ep2 (causal), f1 (has_fact), sk_a (used)
    assert ("ep1", "episode") in node_ids
    assert ("ep2", "episode") in node_ids
    assert ("f1", "fact") in node_ids
    assert ("sk_a", "skill") in node_ids
    # NOT at depth 1: ep3 (needs 2), sk_b (needs 2), f2 (needs 2)
    assert ("ep3", "episode") not in node_ids
    assert ("sk_b", "skill") not in node_ids
    assert ("f2", "fact") not in node_ids


@pytest.mark.asyncio
async def test_lineage_trace_unknown_node(small_graph) -> None:
    """Unknown start id returns ok=True with not_found=True."""
    blocks = await _invoke_tool(
        "hippo_lineage_trace",
        {"start_id": "does_not_exist", "kind": "episode"},
    )
    payload = json.loads(blocks[0])
    assert payload["ok"] is True
    assert payload["nodes"] == []
    assert payload["edges"] == []
    assert payload.get("not_found") is True


@pytest.mark.asyncio
async def test_lineage_trace_edges_have_relation_label(small_graph) -> None:
    """Each edge in response carries a `relation` label so consumers
    can distinguish causal vs has_fact vs used_skill."""
    blocks = await _invoke_tool(
        "hippo_lineage_trace",
        {"start_id": "ep1", "kind": "episode",
         "direction": "forward", "max_depth": 2},
    )
    payload = json.loads(blocks[0])
    relations = {e["relation"] for e in payload["edges"]}
    # We expect at minimum these relations to appear:
    expected_at_least = {"causal", "has_fact", "used_skill"}
    assert expected_at_least.issubset(relations), (
        f"missing relation labels: expected superset of "
        f"{expected_at_least}, got {relations}"
    )
