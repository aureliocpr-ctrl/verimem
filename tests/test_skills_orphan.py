"""FORGIA pezzo #278 — Wave 77: orphan skills (no parents AND no children)."""
from __future__ import annotations

from engram.skill import Skill


def test_empty():
    from engram.skills_orphan import find_orphan_skills

    out = find_orphan_skills([])
    assert out["skills"] == []


def test_isolated_skill_is_orphan():
    from engram.skills_orphan import find_orphan_skills

    skills = [Skill(id="lonely")]
    out = find_orphan_skills(skills)
    assert [s["id"] for s in out["skills"]] == ["lonely"]


def test_has_parent_not_orphan():
    from engram.skills_orphan import find_orphan_skills

    skills = [
        Skill(id="root"),
        Skill(id="child", parent_skills=["root"]),
    ]
    out = find_orphan_skills(skills)
    # child has a parent => not orphan. root has a child => not orphan.
    ids = [s["id"] for s in out["skills"]]
    assert "child" not in ids
    assert "root" not in ids


def test_unknown_parent_still_orphan():
    """Parent reference to non-existent skill: target counts as orphan."""
    from engram.skills_orphan import find_orphan_skills

    skills = [
        Skill(id="dangling", parent_skills=["ghost_parent"]),
    ]
    out = find_orphan_skills(skills)
    ids = [s["id"] for s in out["skills"]]
    assert "dangling" in ids


def test_payload_shape():
    from engram.skills_orphan import find_orphan_skills

    out = find_orphan_skills([])
    for k in ("skills", "n_total"):
        assert k in out
