"""FORGIA pezzo #250 — Wave 49: skill DAG topology stats.

Aggregate stats on the parent_skills DAG: in/out degree distribution,
roots (no parents), leaves (no children), max depth, biggest cluster.

PURE LOCAL.
"""
from __future__ import annotations

from engram.skill import Skill


def test_empty_no_topology():
    from engram.skills_topology import skills_topology

    out = skills_topology([])
    assert out["n_nodes"] == 0
    assert out["roots"] == []


def test_single_skill_is_root_and_leaf():
    from engram.skills_topology import skills_topology

    out = skills_topology([Skill(id="x", name="x")])
    assert out["n_nodes"] == 1
    assert "x" in out["roots"]
    assert "x" in out["leaves"]


def test_root_no_parents():
    from engram.skills_topology import skills_topology

    skills = [
        Skill(id="root", name="r"),
        Skill(id="child", name="c", parent_skills=["root"]),
    ]
    out = skills_topology(skills)
    assert "root" in out["roots"]
    assert "child" not in out["roots"]


def test_leaf_no_children():
    from engram.skills_topology import skills_topology

    skills = [
        Skill(id="parent", name="p"),
        Skill(id="leaf", name="l", parent_skills=["parent"]),
    ]
    out = skills_topology(skills)
    assert "leaf" in out["leaves"]
    assert "parent" not in out["leaves"]


def test_max_depth():
    from engram.skills_topology import skills_topology

    skills = [
        Skill(id="grand", name="g"),
        Skill(id="parent", name="p", parent_skills=["grand"]),
        Skill(id="child", name="c", parent_skills=["parent"]),
    ]
    out = skills_topology(skills)
    # 3 levels = depth 2 (root depth 0).
    assert out["max_depth"] >= 2


def test_in_out_degree_distribution():
    from engram.skills_topology import skills_topology

    skills = [
        Skill(id="root", name="r"),
        Skill(id="c1", name="c1", parent_skills=["root"]),
        Skill(id="c2", name="c2", parent_skills=["root"]),
        Skill(id="c3", name="c3", parent_skills=["root"]),
    ]
    out = skills_topology(skills)
    # root has 3 children (out-degree=3), 0 parents (in-degree=0).
    # Returned distribution has counts.
    assert "out_degree_max" in out
    assert out["out_degree_max"] >= 3


def test_payload_shape_complete():
    from engram.skills_topology import skills_topology

    out = skills_topology([])
    for k in ("n_nodes", "n_edges", "roots", "leaves",
                "max_depth", "out_degree_max", "in_degree_max"):
        assert k in out
