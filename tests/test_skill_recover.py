"""FORGIA pezzo #257 — Wave 56: skill_recover (un-retire).

Restore a retired skill back to candidate so it can earn trials
again. Use case: retired skill was wrongly culled, or upstream
heuristic changed.
"""
from __future__ import annotations

from verimem.skill import Skill


class _FakeSkillsStore:
    def __init__(self, skills: list[Skill]) -> None:
        self._by_id = {s.id: s for s in skills}
        self.stored: list[Skill] = []

    def get(self, sid: str) -> Skill | None:
        return self._by_id.get(sid)

    def store(self, s: Skill) -> None:
        self._by_id[s.id] = s
        self.stored.append(s)


class _FakeAgent:
    def __init__(self, skills: list[Skill]) -> None:
        self.skills = _FakeSkillsStore(skills)


def test_unknown_returns_not_found():
    from verimem.skill_recover import recover_skill

    a = _FakeAgent([])
    out = recover_skill(skill_id="ZZZ", agent=a)
    assert out["found"] is False


def test_recovers_retired_to_candidate():
    from verimem.skill_recover import recover_skill

    sk = Skill(id="x", name="x", status="retired")
    a = _FakeAgent([sk])
    out = recover_skill(skill_id="x", agent=a, apply=True)
    assert out["recovered"] is True
    assert a.skills.get("x").status == "candidate"


def test_non_retired_no_op():
    from verimem.skill_recover import recover_skill

    sk = Skill(id="x", name="x", status="promoted")
    a = _FakeAgent([sk])
    out = recover_skill(skill_id="x", agent=a, apply=True)
    assert out["recovered"] is False
    # Status unchanged.
    assert a.skills.get("x").status == "promoted"


def test_dry_run_no_mutation():
    from verimem.skill_recover import recover_skill

    sk = Skill(id="x", name="x", status="retired")
    a = _FakeAgent([sk])
    out = recover_skill(skill_id="x", agent=a, apply=False)
    assert out["recovered"] is True  # proposed
    assert out["applied"] is False
    assert a.skills.get("x").status == "retired"


def test_payload_shape_complete():
    from verimem.skill_recover import recover_skill

    a = _FakeAgent([])
    out = recover_skill(skill_id="x", agent=a)
    for k in ("skill_id", "found", "recovered", "applied",
                "before_status"):
        assert k in out
