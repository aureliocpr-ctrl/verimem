"""FORGIA pezzo #232 — Wave 31: batch find duplicate skills.

Returns pairs of skills with high Jaccard token similarity on
their signature (name+trigger+body+pre+post). Candidates for
manual merge or auto-dedup.

Different from `hippo_skill_similar` which returns top-k similar
to ONE target. This sweeps the entire library for ALL pairs above
a threshold.
"""
from __future__ import annotations

from engram.skill import Skill


def test_empty_returns_no_pairs():
    from engram.find_duplicates import find_duplicate_skills

    out = find_duplicate_skills([])
    assert out["pairs"] == []


def test_no_duplicates_below_threshold():
    from engram.find_duplicates import find_duplicate_skills

    skills = [
        Skill(id="a", name="alpha beta gamma", trigger="a"),
        Skill(id="b", name="entirely different words", trigger="b"),
    ]
    out = find_duplicate_skills(skills, threshold=0.7)
    assert out["pairs"] == []


def test_identical_skills_detected():
    from engram.find_duplicates import find_duplicate_skills

    skills = [
        Skill(id="a", name="alpha", trigger="trigger one"),
        Skill(id="b", name="alpha", trigger="trigger one"),
    ]
    out = find_duplicate_skills(skills, threshold=0.5)
    assert len(out["pairs"]) == 1
    pair = out["pairs"][0]
    assert {pair["skill_a"], pair["skill_b"]} == {"a", "b"}
    assert pair["jaccard"] >= 0.9


def test_threshold_strict_filters():
    from engram.find_duplicates import find_duplicate_skills

    skills = [
        Skill(id="a", name="alpha beta", trigger="t"),
        Skill(id="b", name="alpha gamma", trigger="t"),
    ]
    # a tokens: {alpha, beta, t}, b tokens: {alpha, gamma, t} → 2/4 = 0.5
    out_strict = find_duplicate_skills(skills, threshold=0.9)
    out_loose = find_duplicate_skills(skills, threshold=0.4)
    assert len(out_strict["pairs"]) == 0
    assert len(out_loose["pairs"]) == 1


def test_pairs_sorted_by_jaccard_desc():
    from engram.find_duplicates import find_duplicate_skills

    skills = [
        Skill(id="a", name="x y z", trigger="x y z"),
        Skill(id="b", name="x y z", trigger="x y z"),  # identical to a
        Skill(id="c", name="x y w", trigger="x y w"),  # partial overlap
    ]
    out = find_duplicate_skills(skills, threshold=0.0)
    jaccards = [p["jaccard"] for p in out["pairs"]]
    assert jaccards == sorted(jaccards, reverse=True)


def test_top_k_respected():
    from engram.find_duplicates import find_duplicate_skills

    skills = [Skill(id=f"s{i}", name="alpha beta gamma") for i in range(5)]
    out = find_duplicate_skills(skills, threshold=0.5, top_k=3)
    assert len(out["pairs"]) <= 3


def test_self_pairs_excluded():
    from engram.find_duplicates import find_duplicate_skills

    skills = [Skill(id="x", name="single")]
    out = find_duplicate_skills(skills)
    assert all(
        p["skill_a"] != p["skill_b"] for p in out["pairs"]
    )


def test_payload_shape_complete():
    from engram.find_duplicates import find_duplicate_skills

    out = find_duplicate_skills([])
    for k in ("pairs", "n_total_skills", "threshold"):
        assert k in out
