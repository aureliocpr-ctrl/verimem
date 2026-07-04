"""FORGIA pezzo #249 — Wave 48: bidirectional skill lineage.

Existing `hippo_skill_lineage` walks `parent_skills` (ancestors).
This adds the descendant direction: skills that have target as
one of THEIR `parent_skills`.

Useful when you want to see "this skill spawned X derived versions"
or "promoting this propagates DOWN to N children".
"""
from __future__ import annotations

from engram.skill import Skill


def test_unknown_returns_not_found():
    from engram.skill_lineage_full import skill_lineage_full

    out = skill_lineage_full(skill_id="ZZZ", all_skills=[])
    assert out["found"] is False


def test_no_relatives():
    from engram.skill_lineage_full import skill_lineage_full

    skills = [Skill(id="alone", name="alone")]
    out = skill_lineage_full(skill_id="alone", all_skills=skills)
    assert out["found"] is True
    assert out["ancestors"] == []
    assert out["descendants"] == []


def test_ancestors_chain():
    from engram.skill_lineage_full import skill_lineage_full

    skills = [
        Skill(id="grand", name="g"),
        Skill(id="parent", name="p", parent_skills=["grand"]),
        Skill(id="child", name="c", parent_skills=["parent"]),
    ]
    out = skill_lineage_full(skill_id="child", all_skills=skills)
    ancestors_ids = [a["id"] for a in out["ancestors"]]
    assert "parent" in ancestors_ids
    assert "grand" in ancestors_ids


def test_descendants_chain():
    from engram.skill_lineage_full import skill_lineage_full

    skills = [
        Skill(id="root", name="root"),
        Skill(id="child1", name="c1", parent_skills=["root"]),
        Skill(id="child2", name="c2", parent_skills=["root"]),
        Skill(id="grandchild", name="gc", parent_skills=["child1"]),
    ]
    out = skill_lineage_full(skill_id="root", all_skills=skills)
    desc_ids = {d["id"] for d in out["descendants"]}
    assert desc_ids == {"child1", "child2", "grandchild"}


def test_cycle_safe():
    from engram.skill_lineage_full import skill_lineage_full

    # Pathological self-reference.
    skills = [
        Skill(id="a", name="a", parent_skills=["b"]),
        Skill(id="b", name="b", parent_skills=["a"]),
    ]
    out = skill_lineage_full(skill_id="a", all_skills=skills)
    # No infinite loop.
    assert "ancestors" in out


def test_depth_per_relative():
    from engram.skill_lineage_full import skill_lineage_full

    skills = [
        Skill(id="grand", name="g"),
        Skill(id="parent", name="p", parent_skills=["grand"]),
        Skill(id="child", name="c", parent_skills=["parent"]),
    ]
    out = skill_lineage_full(skill_id="child", all_skills=skills)
    by_id = {a["id"]: a for a in out["ancestors"]}
    assert by_id["parent"]["depth"] == 1
    assert by_id["grand"]["depth"] == 2


def test_max_depth_caps_traversal():
    from engram.skill_lineage_full import skill_lineage_full

    skills = [Skill(id=f"s{i}", name=f"s{i}") for i in range(10)]
    # Chain s0 <- s1 <- s2 <- ... <- s9 (each parent of next).
    skills[1].parent_skills = ["s0"]
    skills[2].parent_skills = ["s1"]
    skills[3].parent_skills = ["s2"]
    skills[4].parent_skills = ["s3"]
    skills[5].parent_skills = ["s4"]
    out = skill_lineage_full(
        skill_id="s5", all_skills=skills, max_depth=2,
    )
    # Only 2 ancestors visible (s4, s3).
    assert len(out["ancestors"]) <= 2


def test_payload_shape_complete():
    from engram.skill_lineage_full import skill_lineage_full

    out = skill_lineage_full(skill_id="x", all_skills=[])
    for k in ("skill_id", "found", "ancestors", "descendants"):
        assert k in out
