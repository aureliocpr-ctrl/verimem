"""FORGIA pezzo #255 — Wave 54: dashboard overview (read-only mega).

Differs from curate_pipeline (action-oriented): purely READ-ONLY
aggregator. Combines stats + briefing + topology + size +
metrics_one_liner + outcome-breakdown into one snapshot for the
chat-UI dashboard.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from verimem.skill import Skill


@dataclass
class _FakeEp:
    id: str = ""
    task_text: str = ""
    outcome: str = "success"
    tokens_used: int = 0
    pinned: bool = False
    created_at: float = field(default_factory=time.time)
    skills_used: list[str] = field(default_factory=list)


@dataclass
class _FakeFact:
    id: str
    proposition: str = ""
    topic: str = ""
    created_at: float = 0.0


class _FakeSemantic:
    def __init__(self, facts: list[_FakeFact]) -> None:
        self._facts = facts

    def list_facts(self, *, limit=50, offset=0):
        return list(self._facts)[offset:offset + limit]

    def count(self) -> int:
        return len(self._facts)


class _FakeMemory:
    def __init__(self, eps: list[_FakeEp]) -> None:
        self._eps = eps

    def all(self, limit=None):
        return list(self._eps if limit is None else self._eps[:limit])

    def count(self) -> int:
        return len(self._eps)

    def pinned_episodes(self, *, limit=10):
        return [e for e in self._eps if e.pinned][:limit]


class _FakeSkillsStore:
    def __init__(self, skills: list[Skill]) -> None:
        self._skills = skills

    def all(self, status=None):
        if status is None:
            return list(self._skills)
        return [s for s in self._skills if s.status == status]

    def count(self) -> int:
        return len(self._skills)


class _FakeAgent:
    def __init__(self, skills, eps, facts):
        self.skills = _FakeSkillsStore(skills)
        self.memory = _FakeMemory(eps)
        self.semantic = _FakeSemantic(facts)


def test_empty_agent_no_crash():
    from verimem.dashboard_overview import dashboard_overview

    a = _FakeAgent([], [], [])
    out = dashboard_overview(agent=a)
    assert "stats" in out


def test_includes_all_sections():
    from verimem.dashboard_overview import dashboard_overview

    a = _FakeAgent([], [], [])
    out = dashboard_overview(agent=a)
    for k in ("stats", "metrics_summary", "topology",
                "size", "recent_facts", "recent_episodes",
                "top_skills"):
        assert k in out


def test_stats_match_corpus():
    from verimem.dashboard_overview import dashboard_overview

    skills = [Skill(id="s1", name="s1")]
    eps = [_FakeEp("e1"), _FakeEp("e2", outcome="failure")]
    facts = [_FakeFact("f1", "x")]
    a = _FakeAgent(skills, eps, facts)
    out = dashboard_overview(agent=a)
    assert out["stats"]["episodes"] == 2
    assert out["stats"]["skills"] == 1
    assert out["stats"]["facts"] == 1


def test_metrics_summary_is_string():
    from verimem.dashboard_overview import dashboard_overview

    a = _FakeAgent([], [], [])
    out = dashboard_overview(agent=a)
    assert isinstance(out["metrics_summary"], str)
    assert "verimem" in out["metrics_summary"]


def test_topology_section():
    from verimem.dashboard_overview import dashboard_overview

    skills = [Skill(id="root"), Skill(id="leaf", parent_skills=["root"])]
    a = _FakeAgent(skills, [], [])
    out = dashboard_overview(agent=a)
    assert out["topology"]["n_nodes"] == 2
    assert out["topology"]["n_edges"] == 1
