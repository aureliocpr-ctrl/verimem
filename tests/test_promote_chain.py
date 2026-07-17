"""FORGIA pezzo #245 — Wave 44: recursive promote chain.

When a SCHEMA meta-skill (composed via compose_macro) reaches
promotion threshold, its constituent skills should naturally be
promoted too — they provided the recurrent pattern that justified
the meta-skill. This walks `parent_skills` recursively and promotes
all ancestors not yet promoted.

dry-run default; `apply=True` persists via skills.store().
"""
from __future__ import annotations

from verimem.skill import Skill


class _FakeSkillsStore:
    def __init__(self, skills: list[Skill]) -> None:
        self._by_id = {s.id: s for s in skills}
        self.stored: list[Skill] = []

    def get(self, sid: str) -> Skill | None:
        return self._by_id.get(sid)

    def all(self, status: str | None = None) -> list[Skill]:
        return list(self._by_id.values())

    def store(self, s: Skill) -> None:
        self._by_id[s.id] = s
        self.stored.append(s)


class _FakeAgent:
    def __init__(self, skills: list[Skill]) -> None:
        self.skills = _FakeSkillsStore(skills)


def test_unknown_skill_returns_empty():
    from verimem.promote_chain import promote_chain

    a = _FakeAgent([])
    out = promote_chain(skill_id="ZZZ", agent=a)
    assert out["found"] is False
    assert out["promoted"] == []


def test_no_parents_promotes_only_target():
    from verimem.promote_chain import promote_chain

    a = _FakeAgent([Skill(id="x", name="x", status="candidate")])
    out = promote_chain(skill_id="x", agent=a, apply=True)
    assert out["found"] is True
    promoted_ids = [r["id"] for r in out["promoted"]]
    assert promoted_ids == ["x"]


def test_promotes_parent_chain():
    from verimem.promote_chain import promote_chain

    skills = [
        Skill(id="grand", name="g", status="candidate"),
        Skill(id="parent", name="p", status="candidate",
              parent_skills=["grand"]),
        Skill(id="meta", name="m", status="candidate",
              parent_skills=["parent"]),
    ]
    a = _FakeAgent(skills)
    out = promote_chain(skill_id="meta", agent=a, apply=True)
    promoted_ids = {r["id"] for r in out["promoted"]}
    # All 3 (meta + parent + grand) should be promoted.
    assert promoted_ids == {"meta", "parent", "grand"}
    # All in store have status="promoted".
    for s in a.skills.all():
        assert s.status == "promoted"


def test_skip_already_promoted():
    from verimem.promote_chain import promote_chain

    skills = [
        Skill(id="parent", name="p", status="promoted"),
        Skill(id="meta", name="m", status="candidate",
              parent_skills=["parent"]),
    ]
    a = _FakeAgent(skills)
    out = promote_chain(skill_id="meta", agent=a, apply=True)
    # Only `meta` changed.
    skipped_ids = {r["id"] for r in out["skipped_already_promoted"]}
    assert "parent" in skipped_ids
    promoted_ids = {r["id"] for r in out["promoted"]}
    assert promoted_ids == {"meta"}


def test_dry_run_no_mutation():
    from verimem.promote_chain import promote_chain

    skills = [Skill(id="x", name="x", status="candidate")]
    a = _FakeAgent(skills)
    out = promote_chain(skill_id="x", agent=a, apply=False)
    # Status unchanged in store.
    assert a.skills.get("x").status == "candidate"
    # But proposed promotion is reported.
    assert len(out["promoted"]) == 1


def test_handles_cycle_safely():
    """Pathological parent_skills cycle shouldn't infinite-loop."""
    from verimem.promote_chain import promote_chain

    skills = [
        Skill(id="a", name="a", parent_skills=["b"]),
        Skill(id="b", name="b", parent_skills=["a"]),
    ]
    a = _FakeAgent(skills)
    out = promote_chain(skill_id="a", agent=a, apply=True)
    # Both visited once; no infinite recursion.
    assert {r["id"] for r in out["promoted"]} == {"a", "b"}


def test_payload_shape_complete():
    from verimem.promote_chain import promote_chain

    a = _FakeAgent([])
    out = promote_chain(skill_id="x", agent=a)
    for k in ("found", "promoted", "skipped_already_promoted",
                "applied"):
        assert k in out
