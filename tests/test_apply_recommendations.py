"""FORGIA pezzo #233 — Wave 32: apply skill_health recommendations.

Takes the recommended_actions dashboard (#220) and ACTUALLY applies
the suggested status changes (promote/retire) in batch. Dry-run by
default; with apply=True, mutates Skill.status and calls
skills.store().

Useful for housekeeping at the end of a session — instead of
manually promoting/retiring each skill, run this and let the
curation policy do its job.
"""
from __future__ import annotations

from verimem.skill import Skill


class _FakeSkillsStore:
    def __init__(self, skills: list[Skill]) -> None:
        self._by_id = {s.id: s for s in skills}
        self.stored: list[Skill] = []

    def all(self, status: str | None = None) -> list[Skill]:
        if status is None:
            return list(self._by_id.values())
        return [s for s in self._by_id.values() if s.status == status]

    def store(self, s: Skill) -> None:
        self._by_id[s.id] = s
        self.stored.append(s)


class _FakeAgent:
    def __init__(self, skills: list[Skill]) -> None:
        self.skills = _FakeSkillsStore(skills)
        self.memory = type("M", (), {"all": lambda self, limit=None: []})()


def _ready_to_promote() -> Skill:
    """Candidate with strong fitness — should be recommended for promote."""
    return Skill(
        id="ready", name="ready", trials=20, successes=18,
        status="candidate",
    )


def _ready_to_retire() -> Skill:
    return Skill(
        id="bad", name="bad", trials=30, successes=4,
        status="promoted",
    )


def test_dry_run_no_mutation():
    from verimem.apply_recommendations import apply_recommendations

    skills = [_ready_to_promote(), _ready_to_retire()]
    a = _FakeAgent(skills)
    out = apply_recommendations(agent=a, apply=False)
    # No skills mutated.
    assert a.skills.stored == []
    # But the dry-run reports what WOULD change.
    assert out["n_proposed"] >= 2


def test_apply_promote():
    from verimem.apply_recommendations import apply_recommendations

    skills = [_ready_to_promote()]
    a = _FakeAgent(skills)
    out = apply_recommendations(
        agent=a, apply=True, actions=["promote"],
    )
    sk = a.skills.all()[0]
    assert sk.status == "promoted"
    assert out["n_applied"] >= 1


def test_apply_retire():
    from verimem.apply_recommendations import apply_recommendations

    skills = [_ready_to_retire()]
    a = _FakeAgent(skills)
    out = apply_recommendations(
        agent=a, apply=True, actions=["retire"],
    )
    sk = a.skills.all()[0]
    assert sk.status == "retired"


def test_only_listed_actions_applied():
    """When actions=['promote'] only promote runs (retire skipped)."""
    from verimem.apply_recommendations import apply_recommendations

    skills = [_ready_to_promote(), _ready_to_retire()]
    a = _FakeAgent(skills)
    apply_recommendations(
        agent=a, apply=True, actions=["promote"],
    )
    by_id = {s.id: s for s in a.skills.all()}
    assert by_id["ready"].status == "promoted"
    # Retire NOT applied because not in actions.
    assert by_id["bad"].status == "promoted"  # unchanged


def test_change_log_includes_before_after():
    from verimem.apply_recommendations import apply_recommendations

    skills = [_ready_to_promote()]
    a = _FakeAgent(skills)
    out = apply_recommendations(
        agent=a, apply=True, actions=["promote"],
    )
    assert "changes" in out
    change = out["changes"][0]
    for k in ("skill_id", "before_status", "after_status",
                "action", "reasoning"):
        assert k in change
    assert change["before_status"] == "candidate"
    assert change["after_status"] == "promoted"


def test_payload_shape_complete():
    from verimem.apply_recommendations import apply_recommendations

    a = _FakeAgent([])
    out = apply_recommendations(agent=a)
    for k in ("n_proposed", "n_applied", "actions", "changes"):
        assert k in out
