"""FORGIA pezzo #214 — `hippo_briefing` curated session context.

A single MCP call that assembles "everything Claude Code should know
at the start of a conversation" — the same role the SessionStart
hook plays, but available on-demand mid-session ("ricaricami il
contesto memoria"). Outputs a structured dict + a deterministic
summary string.

Sections:
  - `summary_text`: 1-paragraph natural-language brief
  - `stats`: counts (episodes, facts, skills) + breakdown
  - `recent_facts`: top-N declarative facts
  - `pinned_episodes`: never-decay episodes (high priority)
  - `recent_episodes`: most-recent N regardless of pin
  - `top_skills`: by fitness (Beta posterior mean)

Deterministic: given the same fakes the output is byte-stable, so
snapshot tests are possible.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from verimem.skill import Skill

# ---------- Fakes --------------------------------------------------------


@dataclass
class _FakeFact:
    id: str
    proposition: str
    topic: str = ""
    created_at: float = 0.0


@dataclass
class _FakeEp:
    id: str
    task_text: str = ""
    outcome: str = "success"
    pinned: bool = False
    created_at: float = 0.0
    skills_used: list[str] = field(default_factory=list)


class _FakeSemantic:
    def __init__(self, facts: list[_FakeFact]) -> None:
        self._facts = facts

    def list_facts(self, *, limit: int = 50, offset: int = 0):
        ordered = sorted(self._facts, key=lambda f: -f.created_at)
        return ordered[offset:offset + limit]

    def count(self) -> int:
        return len(self._facts)


class _FakeMemory:
    def __init__(self, eps: list[_FakeEp]) -> None:
        self._eps = eps

    def all(self, limit: int | None = None):
        return list(self._eps if limit is None else self._eps[:limit])

    def count(self) -> int:
        return len(self._eps)

    def pinned_episodes(self, *, limit: int = 1000):
        return [e for e in self._eps if getattr(e, "pinned", False)][:limit]


class _FakeSkillsStore:
    def __init__(self, skills: list[Skill]) -> None:
        self._skills = skills

    def all(self, status: str | None = None):
        if status is None:
            return list(self._skills)
        return [s for s in self._skills if s.status == status]

    def count(self) -> int:
        return len(self._skills)


class _FakeAgent:
    def __init__(
        self, skills: list[Skill], episodes: list[_FakeEp],
        facts: list[_FakeFact],
    ) -> None:
        self.skills = _FakeSkillsStore(skills)
        self.memory = _FakeMemory(episodes)
        self.semantic = _FakeSemantic(facts)


# ---------- Tests --------------------------------------------------------


def test_briefing_empty_corpus_returns_zero_counts():
    from verimem.briefing import get_briefing

    a = _FakeAgent(skills=[], episodes=[], facts=[])
    out = get_briefing(agent=a)
    assert out["stats"]["episodes"] == 0
    assert out["stats"]["facts"] == 0
    assert out["stats"]["skills"] == 0
    assert out["recent_facts"] == []
    assert out["pinned_episodes"] == []
    assert out["recent_episodes"] == []
    assert out["top_skills"] == []
    assert isinstance(out["summary_text"], str)


def test_briefing_recent_facts_sorted_newest_first():
    from verimem.briefing import get_briefing

    facts = [
        _FakeFact("f1", "old fact", topic="x", created_at=100.0),
        _FakeFact("f2", "newer fact", topic="x", created_at=200.0),
        _FakeFact("f3", "newest fact", topic="x", created_at=300.0),
    ]
    a = _FakeAgent(skills=[], episodes=[], facts=facts)
    out = get_briefing(agent=a, n_facts=3)
    propositions = [f["proposition"] for f in out["recent_facts"]]
    assert propositions == ["newest fact", "newer fact", "old fact"]


def test_briefing_pinned_episodes_only():
    from verimem.briefing import get_briefing

    eps = [
        _FakeEp("e1", "regular", pinned=False),
        _FakeEp("e2", "important", pinned=True),
        _FakeEp("e3", "also pinned", pinned=True),
    ]
    a = _FakeAgent(skills=[], episodes=eps, facts=[])
    out = get_briefing(agent=a)
    pinned_ids = [e["id"] for e in out["pinned_episodes"]]
    assert "e2" in pinned_ids
    assert "e3" in pinned_ids
    assert "e1" not in pinned_ids


def test_briefing_top_skills_by_fitness():
    """Skills ordered by fitness_mean, highest first."""
    from verimem.briefing import get_briefing

    skills = [
        Skill(id="weak", name="weak_skill", trials=10, successes=2,
              status="promoted"),
        Skill(id="strong", name="strong_skill", trials=10, successes=9,
              status="promoted"),
        Skill(id="mid", name="mid_skill", trials=10, successes=5,
              status="promoted"),
    ]
    a = _FakeAgent(skills=skills, episodes=[], facts=[])
    out = get_briefing(agent=a, n_top_skills=3)
    ids = [s["id"] for s in out["top_skills"]]
    assert ids[0] == "strong"
    assert ids[-1] == "weak"


def test_briefing_summary_mentions_counts():
    """The summary text mentions the corpus sizes."""
    from verimem.briefing import get_briefing

    facts = [_FakeFact("f1", "fact1", created_at=1.0)]
    eps = [_FakeEp("e1", "task1")]
    skills = [Skill(id="s1", name="s1")]
    a = _FakeAgent(skills=skills, episodes=eps, facts=facts)
    out = get_briefing(agent=a)
    s = out["summary_text"].lower()
    assert "episode" in s or "1 ep" in s.lower()
    assert "fact" in s
    assert "skill" in s


def test_briefing_payload_shape_complete():
    """All keys present always, even when sections are empty."""
    from verimem.briefing import get_briefing

    a = _FakeAgent(skills=[], episodes=[], facts=[])
    out = get_briefing(agent=a)
    for key in (
        "summary_text", "stats", "recent_facts",
        "pinned_episodes", "recent_episodes", "top_skills",
    ):
        assert key in out, f"missing key: {key}"


def test_briefing_n_facts_respected():
    """n_facts caps the returned recent_facts list."""
    from verimem.briefing import get_briefing

    facts = [
        _FakeFact(f"f{i}", f"fact{i}", created_at=float(i))
        for i in range(20)
    ]
    a = _FakeAgent(skills=[], episodes=[], facts=facts)
    out = get_briefing(agent=a, n_facts=5)
    assert len(out["recent_facts"]) == 5


def test_briefing_stats_breakdown():
    """Stats include success/failure breakdown for episodes."""
    from verimem.briefing import get_briefing

    eps = [
        _FakeEp("e1", outcome="success"),
        _FakeEp("e2", outcome="success"),
        _FakeEp("e3", outcome="failure"),
    ]
    a = _FakeAgent(skills=[], episodes=eps, facts=[])
    out = get_briefing(agent=a)
    assert out["stats"]["episodes"] == 3
    assert out["stats"]["episodes_success"] == 2
    assert out["stats"]["episodes_failure"] == 1
