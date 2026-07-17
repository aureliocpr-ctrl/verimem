"""FORGIA pezzo #270 — Wave 69: auto-promote skills by threshold.

Batch-promote candidates that meet min_trials + min_fitness.
Different from apply_recommendations (uses full skill_health
policy with lower-bound). This is explicit threshold control.
"""
from __future__ import annotations

from verimem.skill import Skill


class _FakeStore:
    def __init__(self, skills: list[Skill]) -> None:
        self._by_id = {s.id: s for s in skills}
        self.stored: list[Skill] = []

    def all(self, status: str | None = None) -> list[Skill]:
        out = list(self._by_id.values())
        if status is None:
            return out
        return [s for s in out if s.status == status]

    def store(self, s: Skill) -> None:
        self._by_id[s.id] = s
        self.stored.append(s)


class _FakeAgent:
    def __init__(self, skills: list[Skill]) -> None:
        self.skills = _FakeStore(skills)


def test_empty():
    from verimem.skill_promote_threshold import promote_by_threshold

    a = _FakeAgent([])
    out = promote_by_threshold(agent=a)
    assert out["proposed"] == []


def test_promotes_above_threshold():
    from verimem.skill_promote_threshold import promote_by_threshold

    skills = [
        Skill(id="good", status="candidate", trials=10, successes=8),
        Skill(id="bad", status="candidate", trials=10, successes=3),
    ]
    a = _FakeAgent(skills)
    out = promote_by_threshold(
        agent=a, min_trials=5, min_fitness=0.6, apply=True,
    )
    ids = [s["skill_id"] for s in out["proposed"]]
    assert "good" in ids
    assert "bad" not in ids
    assert a.skills._by_id["good"].status == "promoted"


def test_low_trials_skipped():
    from verimem.skill_promote_threshold import promote_by_threshold

    skills = [
        Skill(id="few", status="candidate", trials=2, successes=2),
    ]
    a = _FakeAgent(skills)
    out = promote_by_threshold(agent=a, min_trials=5)
    assert out["proposed"] == []


def test_non_candidate_skipped():
    from verimem.skill_promote_threshold import promote_by_threshold

    skills = [
        Skill(id="r", status="retired", trials=10, successes=9),
    ]
    a = _FakeAgent(skills)
    out = promote_by_threshold(agent=a)
    assert out["proposed"] == []


def test_dry_run_no_mutation():
    from verimem.skill_promote_threshold import promote_by_threshold

    skills = [Skill(id="x", status="candidate", trials=10, successes=8)]
    a = _FakeAgent(skills)
    out = promote_by_threshold(agent=a, apply=False)
    # Proposed but not applied.
    assert len(out["proposed"]) == 1
    assert a.skills._by_id["x"].status == "candidate"


def test_payload_shape():
    from verimem.skill_promote_threshold import promote_by_threshold

    a = _FakeAgent([])
    out = promote_by_threshold(agent=a)
    for k in ("proposed", "n_proposed", "n_applied", "applied"):
        assert k in out
