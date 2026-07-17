"""FORGIA pezzo #272 — Wave 71: composite corpus health 0-100."""
from __future__ import annotations

from dataclasses import dataclass, field

from verimem.skill import Skill


@dataclass
class _FakeEp:
    outcome: str = "success"
    skills_used: list[str] = field(default_factory=list)


class _FakeSkillsStore:
    def __init__(self, skills: list[Skill]) -> None:
        self._skills = skills

    def all(self, status=None) -> list[Skill]:
        if status is None:
            return list(self._skills)
        return [s for s in self._skills if s.status == status]


class _FakeMemory:
    def __init__(self, eps):
        self._eps = eps

    def all(self, limit=None):
        return list(self._eps)


class _FakeAgent:
    def __init__(self, skills, eps):
        self.skills = _FakeSkillsStore(skills)
        self.memory = _FakeMemory(eps)


def test_empty_returns_neutral():
    from verimem.corpus_health_score import compute_health_score

    a = _FakeAgent([], [])
    out = compute_health_score(agent=a)
    # Empty corpus → neutral score around 50.
    assert 0 <= out["score"] <= 100


def test_high_success_high_promoted_high_score():
    from verimem.corpus_health_score import compute_health_score

    skills = [
        Skill(id=f"s{i}", status="promoted", trials=10, successes=9)
        for i in range(5)
    ]
    eps = [_FakeEp("success") for _ in range(10)]
    a = _FakeAgent(skills, eps)
    out = compute_health_score(agent=a)
    assert out["score"] >= 70


def test_all_failure_low_score():
    from verimem.corpus_health_score import compute_health_score

    skills = [
        Skill(id=f"s{i}", status="candidate", trials=10, successes=1)
        for i in range(5)
    ]
    eps = [_FakeEp("failure") for _ in range(10)]
    a = _FakeAgent(skills, eps)
    out = compute_health_score(agent=a)
    assert out["score"] < 50


def test_includes_components():
    from verimem.corpus_health_score import compute_health_score

    a = _FakeAgent([], [])
    out = compute_health_score(agent=a)
    assert "components" in out


def test_payload_shape():
    from verimem.corpus_health_score import compute_health_score

    a = _FakeAgent([], [])
    out = compute_health_score(agent=a)
    for k in ("score", "components", "verdict"):
        assert k in out


def test_verdict_string():
    from verimem.corpus_health_score import compute_health_score

    a = _FakeAgent([], [])
    out = compute_health_score(agent=a)
    assert isinstance(out["verdict"], str)
    assert len(out["verdict"]) > 3
