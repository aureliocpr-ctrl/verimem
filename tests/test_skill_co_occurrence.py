"""FORGIA pezzo #225 — Wave 24: skill co-occurrence (symmetric).

Different from SR transitions (asymmetric, ordered): co-occurrence
counts how often two skills appear in the SAME episode regardless
of order.

Useful for:
  - "which skills tend to be used together?"
  - bundle discovery (FORGIA pezzo #170 lateral inhibition input)
  - cluster analysis at a different granularity than SR
"""
from __future__ import annotations

from dataclasses import dataclass, field

from engram.skill import Skill


@dataclass
class _FakeEp:
    skills_used: list[str] = field(default_factory=list)


def test_empty_returns_empty_pairs():
    from engram.skill_co_occurrence import skill_co_occurrence

    out = skill_co_occurrence(skills=[], episodes=[])
    assert out["pairs"] == []
    assert out["n_episodes"] == 0


def test_single_skill_in_episode_no_pairs():
    from engram.skill_co_occurrence import skill_co_occurrence

    skills = [Skill(id="A", name="A")]
    eps = [_FakeEp(["A"])]
    out = skill_co_occurrence(skills=skills, episodes=eps)
    assert out["pairs"] == []  # no pair, only one skill


def test_two_skills_co_occur():
    from engram.skill_co_occurrence import skill_co_occurrence

    skills = [Skill(id="A", name="A"), Skill(id="B", name="B")]
    eps = [
        _FakeEp(["A", "B"]),
        _FakeEp(["A", "B"]),
        _FakeEp(["A"]),
    ]
    out = skill_co_occurrence(skills=skills, episodes=eps)
    assert len(out["pairs"]) == 1
    pair = out["pairs"][0]
    assert pair["count"] == 2
    assert {pair["skill_a"], pair["skill_b"]} == {"A", "B"}


def test_jaccard_correct():
    """Jaccard(A, B) = |A ∩ B| / |A ∪ B| over episodes containing
    each skill."""
    from engram.skill_co_occurrence import skill_co_occurrence

    skills = [Skill(id="A", name="A"), Skill(id="B", name="B")]
    eps = [
        _FakeEp(["A", "B"]),  # both
        _FakeEp(["A", "B"]),  # both
        _FakeEp(["A"]),       # A only
        _FakeEp(["B"]),       # B only
    ]
    # |A ∩ B| = 2 episodes, |A ∪ B| = 4 episodes → 0.5.
    out = skill_co_occurrence(skills=skills, episodes=eps)
    pair = out["pairs"][0]
    assert abs(pair["jaccard"] - 0.5) < 1e-9


def test_pairs_sorted_by_count_desc():
    from engram.skill_co_occurrence import skill_co_occurrence

    skills = [Skill(id=x, name=x) for x in ("A", "B", "C")]
    eps = [
        _FakeEp(["A", "B"]),
        _FakeEp(["A", "B"]),
        _FakeEp(["A", "B"]),
        _FakeEp(["A", "C"]),
    ]
    out = skill_co_occurrence(skills=skills, episodes=eps)
    counts = [p["count"] for p in out["pairs"]]
    assert counts == sorted(counts, reverse=True)


def test_top_pairs_respected():
    from engram.skill_co_occurrence import skill_co_occurrence

    skills = [Skill(id=x, name=x) for x in "ABCDE"]
    eps = [
        _FakeEp(["A", "B", "C", "D", "E"]),  # 10 distinct pairs
        _FakeEp(["A", "B", "C", "D", "E"]),
    ]
    out = skill_co_occurrence(
        skills=skills, episodes=eps, top_pairs=3,
    )
    assert len(out["pairs"]) == 3


def test_self_pairs_excluded():
    """A skill paired with itself is not a meaningful co-occurrence."""
    from engram.skill_co_occurrence import skill_co_occurrence

    skills = [Skill(id="A", name="A"), Skill(id="B", name="B")]
    eps = [_FakeEp(["A", "A", "B"])]
    out = skill_co_occurrence(skills=skills, episodes=eps)
    pair_ids = [(p["skill_a"], p["skill_b"]) for p in out["pairs"]]
    assert ("A", "A") not in pair_ids
    assert ("B", "B") not in pair_ids


def test_payload_shape_complete():
    from engram.skill_co_occurrence import skill_co_occurrence

    out = skill_co_occurrence(skills=[], episodes=[])
    for k in ("pairs", "n_episodes", "n_skills"):
        assert k in out
