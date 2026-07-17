"""R43: Export memory as a knowledge graph (nodes + edges)."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class _Ep:
    id: str
    task_text: str
    skills_used: list[str] = field(default_factory=list)
    outcome: str = "success"


@dataclass
class _Skill:
    id: str
    name: str = ""
    parent_skills: list[str] = field(default_factory=list)


@dataclass
class _Fact:
    id: str
    proposition: str
    topic: str = ""


def test_empty_returns_empty_graph():
    from verimem.knowledge_graph_export import export_graph
    out = export_graph(episodes=[], skills=[], facts=[])
    assert out["nodes"] == []
    assert out["edges"] == []


def test_skill_nodes_and_parent_edges():
    from verimem.knowledge_graph_export import export_graph
    skills = [_Skill("root"), _Skill("child", parent_skills=["root"])]
    out = export_graph(episodes=[], skills=skills, facts=[])
    types = {n["type"] for n in out["nodes"]}
    assert "skill" in types
    # at least 1 parent edge
    has_parent = any(e["type"] == "parent_of" for e in out["edges"])
    assert has_parent


def test_episode_uses_skill_edges():
    from verimem.knowledge_graph_export import export_graph
    eps = [_Ep("e1", "task", skills_used=["s1"])]
    skills = [_Skill("s1")]
    out = export_graph(episodes=eps, skills=skills, facts=[])
    # Edge episode→skill
    has = any(e["type"] == "uses_skill" for e in out["edges"])
    assert has


def test_fact_nodes_included():
    from verimem.knowledge_graph_export import export_graph
    facts = [_Fact("f1", "X")]
    out = export_graph(episodes=[], skills=[], facts=facts)
    types = {n["type"] for n in out["nodes"]}
    assert "fact" in types


def test_payload_shape():
    from verimem.knowledge_graph_export import export_graph
    out = export_graph(episodes=[], skills=[], facts=[])
    for k in ("nodes", "edges", "n_nodes", "n_edges"):
        assert k in out


def test_node_keys():
    from verimem.knowledge_graph_export import export_graph
    skills = [_Skill("s1")]
    out = export_graph(episodes=[], skills=skills, facts=[])
    if out["nodes"]:
        for k in ("id", "type", "label"):
            assert k in out["nodes"][0]
