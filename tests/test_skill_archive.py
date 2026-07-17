"""FORGIA pezzo #251 — Wave 50: skill archive (export + retire).

Atomic op: export the skill as portable JSON AND set status="retired".
Useful end-of-life flow: keep a snapshot before retiring.
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


def test_unknown_skill():
    from verimem.skill_archive import archive_skill

    a = _FakeAgent([])
    out = archive_skill(skill_id="ZZZ", agent=a)
    assert out["found"] is False


def test_dry_run_exports_no_mutation():
    from verimem.skill_archive import archive_skill

    sk = Skill(id="x", name="my_skill", status="promoted")
    a = _FakeAgent([sk])
    out = archive_skill(skill_id="x", agent=a, apply=False)
    assert out["found"] is True
    assert out["applied"] is False
    assert out["exported"]["id"] == "x"
    assert out["exported"]["name"] == "my_skill"
    # Status unchanged in store.
    assert a.skills.get("x").status == "promoted"


def test_apply_retires():
    from verimem.skill_archive import archive_skill

    sk = Skill(id="x", name="x", status="promoted")
    a = _FakeAgent([sk])
    out = archive_skill(skill_id="x", agent=a, apply=True)
    assert out["applied"] is True
    assert a.skills.get("x").status == "retired"


def test_already_retired_no_op():
    from verimem.skill_archive import archive_skill

    sk = Skill(id="x", name="x", status="retired")
    a = _FakeAgent([sk])
    out = archive_skill(skill_id="x", agent=a, apply=True)
    # No status change to write but exported anyway.
    assert out["exported"]["id"] == "x"


def test_payload_shape_complete():
    from verimem.skill_archive import archive_skill

    a = _FakeAgent([])
    out = archive_skill(skill_id="x", agent=a)
    for k in ("skill_id", "found", "applied", "exported"):
        assert k in out
