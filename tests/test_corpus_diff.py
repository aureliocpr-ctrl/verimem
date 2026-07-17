"""FORGIA pezzo #218 — Wave 17: corpus diff (timeline of changes).

Given a `since` timestamp, returns what's been added/modified across
the 3 memory tiers. Useful for:
  - "what's changed since I last opened the project?"
  - "what facts has the agent learned this week?"
  - "which skills crossed the promote/retire threshold today?"

Sections:
  - `new_facts`: facts.created_at >= since
  - `new_episodes`: episodes.created_at >= since
  - `updated_skills`: skills.updated_at >= since (fitness/trials change)
  - `outcome_breakdown`: success/failure counts in window

Six invariants:
  1. since=now → all sections empty.
  2. since=0 → returns ALL.
  3. new facts filtered by created_at.
  4. updated skills returned with delta info.
  5. outcome breakdown counts.
  6. since-too-far-in-future → empty.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from verimem.skill import Skill


@dataclass
class _FakeFact:
    id: str
    proposition: str = ""
    topic: str = ""
    created_at: float = 0.0


@dataclass
class _FakeEp:
    id: str
    task_text: str = ""
    outcome: str = "success"
    created_at: float = 0.0
    skills_used: list[str] = field(default_factory=list)


class _FakeSemantic:
    def __init__(self, facts: list[_FakeFact]) -> None:
        self._facts = facts

    def list_facts(self, *, limit: int = 1000, offset: int = 0):
        return list(self._facts)[offset:offset + limit]


class _FakeMemory:
    def __init__(self, eps: list[_FakeEp]) -> None:
        self._eps = eps

    def all(self, limit: int | None = None):
        return list(self._eps if limit is None else self._eps[:limit])


class _FakeSkillsStore:
    def __init__(self, skills: list[Skill]) -> None:
        self._skills = skills

    def all(self, status: str | None = None) -> list[Skill]:
        if status is None:
            return list(self._skills)
        return [s for s in self._skills if s.status == status]


class _FakeAgent:
    def __init__(
        self, skills: list[Skill], episodes: list[_FakeEp],
        facts: list[_FakeFact],
    ) -> None:
        self.skills = _FakeSkillsStore(skills)
        self.memory = _FakeMemory(episodes)
        self.semantic = _FakeSemantic(facts)


def test_diff_now_returns_empty():
    """`since` = now: nothing is "after now", everything filtered."""
    from verimem.corpus_diff import corpus_diff

    now = time.time()
    facts = [_FakeFact("f1", "old", created_at=now - 1000)]
    eps = [_FakeEp("e1", "old", created_at=now - 1000)]
    skills = [Skill(id="s1", name="s1", updated_at=now - 1000)]
    a = _FakeAgent(skills=skills, episodes=eps, facts=facts)
    out = corpus_diff(agent=a, since=now)
    assert out["new_facts"] == []
    assert out["new_episodes"] == []
    assert out["updated_skills"] == []


def test_diff_zero_returns_all():
    from verimem.corpus_diff import corpus_diff

    facts = [_FakeFact("f1", "fact", created_at=100.0)]
    eps = [_FakeEp("e1", "task", created_at=200.0)]
    skills = [Skill(id="s1", name="s1", updated_at=300.0)]
    a = _FakeAgent(skills=skills, episodes=eps, facts=facts)
    out = corpus_diff(agent=a, since=0.0)
    assert len(out["new_facts"]) == 1
    assert len(out["new_episodes"]) == 1
    assert len(out["updated_skills"]) == 1


def test_diff_new_facts_filtered_by_created_at():
    from verimem.corpus_diff import corpus_diff

    facts = [
        _FakeFact("old", "old fact", created_at=100.0),
        _FakeFact("new", "new fact", created_at=300.0),
    ]
    a = _FakeAgent(skills=[], episodes=[], facts=facts)
    out = corpus_diff(agent=a, since=200.0)
    ids = [f["id"] for f in out["new_facts"]]
    assert "new" in ids
    assert "old" not in ids


def test_diff_outcome_breakdown():
    from verimem.corpus_diff import corpus_diff

    eps = [
        _FakeEp("e1", outcome="success", created_at=300.0),
        _FakeEp("e2", outcome="success", created_at=300.0),
        _FakeEp("e3", outcome="failure", created_at=300.0),
        _FakeEp("e4", outcome="success", created_at=50.0),  # outside window
    ]
    a = _FakeAgent(skills=[], episodes=eps, facts=[])
    out = corpus_diff(agent=a, since=200.0)
    assert out["outcome_breakdown"]["success"] == 2
    assert out["outcome_breakdown"]["failure"] == 1


def test_diff_updated_skills_carries_delta():
    """Updated skills include their current fitness so the user can
    see the post-update state."""
    from verimem.corpus_diff import corpus_diff

    skills = [
        Skill(id="s1", name="newly_updated", trials=5, successes=3,
              updated_at=300.0),
    ]
    a = _FakeAgent(skills=skills, episodes=[], facts=[])
    out = corpus_diff(agent=a, since=200.0)
    assert len(out["updated_skills"]) == 1
    s = out["updated_skills"][0]
    assert s["id"] == "s1"
    assert "fitness_mean" in s
    assert s["trials"] == 5


def test_diff_since_far_future_empty():
    from verimem.corpus_diff import corpus_diff

    facts = [_FakeFact("f1", "f", created_at=time.time())]
    a = _FakeAgent(skills=[], episodes=[], facts=facts)
    far = time.time() + 1e9
    out = corpus_diff(agent=a, since=far)
    assert out["new_facts"] == []


def test_diff_payload_shape_complete():
    from verimem.corpus_diff import corpus_diff

    a = _FakeAgent(skills=[], episodes=[], facts=[])
    out = corpus_diff(agent=a, since=0.0)
    for key in ("since", "new_facts", "new_episodes",
                "updated_skills", "outcome_breakdown", "summary"):
        assert key in out
