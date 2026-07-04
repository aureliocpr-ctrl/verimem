"""FORGIA pezzo #254 — Wave 53: merge a skill pair atomically.

Apply the suggestion from find_duplicate_skills (#232): take 2
near-duplicate skills, fold the secondary into the primary,
retire the secondary. Trials and successes accumulate; lineage
records the merge.

Different from existing `hippo_skill_merge` (manual): this
specifically targets find_duplicate output and handles the
trial-accumulation correctly.
"""
from __future__ import annotations

from engram.skill import Skill


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


def test_unknown_skill_returns_error():
    from engram.skill_merge_pair import merge_skill_pair

    a = _FakeAgent([])
    out = merge_skill_pair(skill_id_a="x", skill_id_b="y", agent=a)
    assert out["ok"] is False


def test_keeper_a_default_trials_summed():
    from engram.skill_merge_pair import merge_skill_pair

    skills = [
        Skill(id="a", name="primary", trials=10, successes=8),
        Skill(id="b", name="secondary", trials=5, successes=4),
    ]
    ag = _FakeAgent(skills)
    out = merge_skill_pair(
        skill_id_a="a", skill_id_b="b", agent=ag, apply=True,
    )
    assert out["ok"] is True
    primary = ag.skills.get("a")
    assert primary.trials == 15
    assert primary.successes == 12


def test_secondary_retired_after_merge():
    from engram.skill_merge_pair import merge_skill_pair

    skills = [
        Skill(id="a", name="a", trials=5, successes=3),
        Skill(id="b", name="b", trials=2, successes=2),
    ]
    ag = _FakeAgent(skills)
    merge_skill_pair(
        skill_id_a="a", skill_id_b="b", agent=ag, apply=True,
    )
    secondary = ag.skills.get("b")
    assert secondary.status == "retired"


def test_lineage_includes_secondary():
    from engram.skill_merge_pair import merge_skill_pair

    skills = [
        Skill(id="a", name="a"),
        Skill(id="b", name="b"),
    ]
    ag = _FakeAgent(skills)
    merge_skill_pair(
        skill_id_a="a", skill_id_b="b", agent=ag, apply=True,
    )
    primary = ag.skills.get("a")
    assert "b" in primary.parent_skills


def test_keeper_b_inverts_direction():
    from engram.skill_merge_pair import merge_skill_pair

    skills = [
        Skill(id="a", name="a", trials=3, successes=2),
        Skill(id="b", name="b", trials=7, successes=5),
    ]
    ag = _FakeAgent(skills)
    out = merge_skill_pair(
        skill_id_a="a", skill_id_b="b", agent=ag,
        keeper="b", apply=True,
    )
    assert out["primary_id"] == "b"
    primary = ag.skills.get("b")
    assert primary.trials == 10
    secondary = ag.skills.get("a")
    assert secondary.status == "retired"


def test_dry_run_no_mutation():
    from engram.skill_merge_pair import merge_skill_pair

    skills = [
        Skill(id="a", name="a", trials=10),
        Skill(id="b", name="b", trials=5),
    ]
    ag = _FakeAgent(skills)
    out = merge_skill_pair(
        skill_id_a="a", skill_id_b="b", agent=ag, apply=False,
    )
    primary = ag.skills.get("a")
    secondary = ag.skills.get("b")
    # Counts unchanged.
    assert primary.trials == 10
    assert secondary.trials == 5
    assert secondary.status != "retired"
    # But proposed result shown.
    assert out["proposed_trials"] == 15


def test_payload_shape_complete():
    from engram.skill_merge_pair import merge_skill_pair

    a = _FakeAgent([])
    out = merge_skill_pair(skill_id_a="x", skill_id_b="y", agent=a)
    for k in ("ok", "primary_id", "secondary_id", "applied"):
        assert k in out
