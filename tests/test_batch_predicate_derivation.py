"""FORGIA pezzo #215 — Wave 14: batch predicate derivation.

Pezzo #213 derives pre/post for ONE skill on demand. Pezzo #215
runs the same heuristic across the ENTIRE skill library in one
sweep — bootstrapping the predicate graph from the existing episode
corpus.

This is the game-changer for STRIPS: the live library has 318
skills with empty pre/post (v1 schema). After one batch run,
60-70% of skills will have derived predicates and the planner
becomes useful on real data — without a single LLM call.

Modes:
  - dry-run (default): returns the per-skill predicates that WOULD
    be applied, plus aggregate stats. No mutation.
  - apply=true: writes the derived predicates back via
    `skills.store()` for each skill that has new predicates.

Optimization: a single pass over the episodes builds a global
predecessor count, then we lookup per skill — O(E + S) instead
of O(E*S).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from engram.skill import Skill


@dataclass
class _FakeEp:
    skills_used: list[str] = field(default_factory=list)


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


class _FakeMemory:
    def __init__(self, eps: list[_FakeEp]) -> None:
        self._eps = eps

    def all(self, limit: int | None = None) -> list[_FakeEp]:
        return list(self._eps if limit is None else self._eps[:limit])


class _FakeAgent:
    def __init__(
        self, skills: list[Skill], episodes: list[_FakeEp],
    ) -> None:
        self.skills = _FakeSkillsStore(skills)
        self.memory = _FakeMemory(episodes)


def test_batch_returns_per_skill_payload():
    """Output includes one entry per processed skill with derived
    pre/post (dry-run by default)."""
    from engram.predicate_derivation import derive_predicates_batch

    skills = [
        Skill(id="A", name="alpha"),
        Skill(id="B", name="beta"),
    ]
    eps = [_FakeEp(["A", "B"]), _FakeEp(["A", "B"])]
    a = _FakeAgent(skills, eps)
    out = derive_predicates_batch(agent=a, threshold=0.5)
    assert "skills" in out
    assert len(out["skills"]) == 2
    by_id = {s["id"]: s for s in out["skills"]}
    # B is preceded by A 100% → after_A in pre.
    assert "after_A" in by_id["B"]["preconditions"]
    # A is first in episode always → no predecessor.
    assert by_id["A"]["preconditions"] == []
    # Both get the trivial post.
    assert by_id["A"]["postconditions"] == ["after_A"]
    assert by_id["B"]["postconditions"] == ["after_B"]


def test_batch_aggregate_stats():
    from engram.predicate_derivation import derive_predicates_batch

    skills = [
        Skill(id="A", name="alpha"),
        Skill(id="B", name="beta"),
        Skill(id="C", name="gamma"),
    ]
    eps = [_FakeEp(["A", "B", "C"])] * 5
    a = _FakeAgent(skills, eps)
    out = derive_predicates_batch(agent=a, threshold=0.5)
    assert "stats" in out
    assert out["stats"]["n_skills_processed"] == 3
    # B and C have a non-trivial precondition (not just self-marker).
    # A has no precondition (always first).
    assert out["stats"]["n_with_preconditions"] == 2
    assert out["stats"]["applied"] is False


def test_batch_dry_run_does_not_mutate():
    from engram.predicate_derivation import derive_predicates_batch

    skills = [Skill(id="A", name="a"), Skill(id="B", name="b")]
    eps = [_FakeEp(["A", "B"])] * 3
    a = _FakeAgent(skills, eps)
    out = derive_predicates_batch(agent=a, apply=False)
    # Skills in store should still have empty pre/post.
    for s in a.skills.all():
        assert s.preconditions == []
        assert s.postconditions == []
    assert a.skills.stored == []


def test_batch_apply_persists_changes():
    from engram.predicate_derivation import derive_predicates_batch

    skills = [Skill(id="A", name="a"), Skill(id="B", name="b")]
    eps = [_FakeEp(["A", "B"])] * 3
    a = _FakeAgent(skills, eps)
    out = derive_predicates_batch(agent=a, apply=True)
    assert out["stats"]["applied"] is True
    # B in store now has the derived precondition.
    b = next(s for s in a.skills.all() if s.id == "B")
    assert "after_A" in b.preconditions
    assert "after_B" in b.postconditions


def test_batch_skips_skills_already_having_predicates():
    """Skills that already have pre/post are NOT overwritten when
    `overwrite=False` (default)."""
    from engram.predicate_derivation import derive_predicates_batch

    pre_existing = Skill(
        id="B", name="b",
        preconditions=["already_set"],
        postconditions=["already_done"],
    )
    skills = [Skill(id="A", name="a"), pre_existing]
    eps = [_FakeEp(["A", "B"])] * 3
    a = _FakeAgent(skills, eps)
    out = derive_predicates_batch(agent=a, apply=True, overwrite=False)
    b = next(s for s in a.skills.all() if s.id == "B")
    # B's existing predicates preserved.
    assert b.preconditions == ["already_set"]
    assert b.postconditions == ["already_done"]
    assert out["stats"]["n_skipped_existing"] >= 1


def test_batch_overwrite_replaces_existing():
    """With overwrite=True, derived predicates overwrite existing."""
    from engram.predicate_derivation import derive_predicates_batch

    pre_existing = Skill(
        id="B", name="b",
        preconditions=["wrong_old"],
    )
    skills = [Skill(id="A", name="a"), pre_existing]
    eps = [_FakeEp(["A", "B"])] * 3
    a = _FakeAgent(skills, eps)
    derive_predicates_batch(
        agent=a, apply=True, overwrite=True,
    )
    b = next(s for s in a.skills.all() if s.id == "B")
    assert b.preconditions == ["after_A"]
    assert "wrong_old" not in b.preconditions


def test_batch_threshold_propagated():
    """The threshold parameter affects per-skill derivation."""
    from engram.predicate_derivation import derive_predicates_batch

    skills = [Skill(id="A", name="a"), Skill(id="B", name="b"),
                Skill(id="C", name="c")]
    eps = [
        _FakeEp(["A", "C"]),
        _FakeEp(["B", "C"]),
    ]
    a = _FakeAgent(skills, eps)
    # 0.6: each predecessor at 0.5, none qualifies.
    out_strict = derive_predicates_batch(agent=a, threshold=0.6)
    by_strict = {s["id"]: s for s in out_strict["skills"]}
    assert "after_A" not in by_strict["C"]["preconditions"]
    # 0.4: both qualify.
    out_loose = derive_predicates_batch(agent=a, threshold=0.4)
    by_loose = {s["id"]: s for s in out_loose["skills"]}
    assert "after_A" in by_loose["C"]["preconditions"]
    assert "after_B" in by_loose["C"]["preconditions"]


def test_batch_empty_episodes_only_post():
    """Empty corpus → all skills get only the trivial postcondition."""
    from engram.predicate_derivation import derive_predicates_batch

    skills = [Skill(id="A", name="a"), Skill(id="B", name="b")]
    a = _FakeAgent(skills, [])
    out = derive_predicates_batch(agent=a)
    for s in out["skills"]:
        assert s["preconditions"] == []
        assert s["postconditions"] == [f"after_{s['id']}"]
