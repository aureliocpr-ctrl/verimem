"""FORGIA pezzo #268 — Wave 67: find skills with predicate X in
pre or post."""
from __future__ import annotations

from verimem.skill import Skill


def test_empty():
    from verimem.skills_search_by_predicate import skills_with_predicate

    out = skills_with_predicate([], predicate="x")
    assert out["skills"] == []


def test_finds_in_preconditions():
    from verimem.skills_search_by_predicate import skills_with_predicate

    skills = [
        Skill(id="a", preconditions=["target"], postconditions=[]),
        Skill(id="b", preconditions=["other"], postconditions=[]),
    ]
    out = skills_with_predicate(skills, predicate="target")
    ids = [s["id"] for s in out["skills"]]
    assert ids == ["a"]


def test_finds_in_postconditions():
    from verimem.skills_search_by_predicate import skills_with_predicate

    skills = [
        Skill(id="a", preconditions=[], postconditions=["target"]),
        Skill(id="b", preconditions=[], postconditions=["other"]),
    ]
    out = skills_with_predicate(skills, predicate="target")
    ids = [s["id"] for s in out["skills"]]
    assert ids == ["a"]


def test_side_pre_only():
    from verimem.skills_search_by_predicate import skills_with_predicate

    skills = [
        Skill(id="a", preconditions=["x"]),
        Skill(id="b", postconditions=["x"]),
    ]
    out = skills_with_predicate(skills, predicate="x", side="pre")
    ids = [s["id"] for s in out["skills"]]
    assert ids == ["a"]


def test_side_post_only():
    from verimem.skills_search_by_predicate import skills_with_predicate

    skills = [
        Skill(id="a", preconditions=["x"]),
        Skill(id="b", postconditions=["x"]),
    ]
    out = skills_with_predicate(skills, predicate="x", side="post")
    ids = [s["id"] for s in out["skills"]]
    assert ids == ["b"]


def test_includes_side_marker():
    from verimem.skills_search_by_predicate import skills_with_predicate

    skills = [Skill(id="a", preconditions=["x"], postconditions=["x"])]
    out = skills_with_predicate(skills, predicate="x")
    s = out["skills"][0]
    assert "in_pre" in s
    assert "in_post" in s
    assert s["in_pre"] is True
    assert s["in_post"] is True


def test_payload_shape():
    from verimem.skills_search_by_predicate import skills_with_predicate

    out = skills_with_predicate([], predicate="x")
    for k in ("predicate", "side", "skills", "n_total"):
        assert k in out
