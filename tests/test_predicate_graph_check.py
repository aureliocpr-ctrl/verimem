"""FORGIA pezzo #229 — Wave 28: predicate-graph DAG validation.

After Wave 12+15 we may have hundreds of skills with auto-derived
preconditions/postconditions. The STRIPS planner is much faster
when the resulting predicate graph is acyclic. This tool detects
cycles + isolated nodes so the user can act on inconsistencies.

Edge model: skill_a → skill_b iff
  set(skill_a.postconditions) ∩ set(skill_b.preconditions) ≠ ∅

Cycle: sequence of skills s_1 → s_2 → ... → s_n → s_1.
"""
from __future__ import annotations

from verimem.skill import Skill


def test_empty_graph_no_cycles():
    from verimem.predicate_graph_check import predicate_graph_check

    out = predicate_graph_check([])
    assert out["has_cycles"] is False
    assert out["cycles"] == []
    assert out["n_nodes"] == 0


def test_linear_chain_no_cycles():
    from verimem.predicate_graph_check import predicate_graph_check

    skills = [
        Skill(id="A", name="A", postconditions=["X"]),
        Skill(id="B", name="B", preconditions=["X"], postconditions=["Y"]),
        Skill(id="C", name="C", preconditions=["Y"], postconditions=["Z"]),
    ]
    out = predicate_graph_check(skills)
    assert out["has_cycles"] is False
    # 2 edges: A→B, B→C.
    assert out["n_edges"] == 2


def test_simple_cycle_detected():
    """A.post = X, B.pre = X, B.post = Y, A.pre = Y → A → B → A."""
    from verimem.predicate_graph_check import predicate_graph_check

    skills = [
        Skill(id="A", name="A", preconditions=["Y"], postconditions=["X"]),
        Skill(id="B", name="B", preconditions=["X"], postconditions=["Y"]),
    ]
    out = predicate_graph_check(skills)
    assert out["has_cycles"] is True
    assert len(out["cycles"]) >= 1


def test_self_loop_detected():
    """skill X has pre and post sharing a predicate → self-edge."""
    from verimem.predicate_graph_check import predicate_graph_check

    skills = [
        Skill(id="X", name="X",
              preconditions=["P"], postconditions=["P", "Q"]),
    ]
    out = predicate_graph_check(skills)
    # Self-loop is a cycle.
    assert out["has_cycles"] is True


def test_isolated_skills_listed():
    """Skills with neither pre nor post that match other skills are
    'isolated' — no incoming/outgoing edges."""
    from verimem.predicate_graph_check import predicate_graph_check

    skills = [
        Skill(id="A", name="A", postconditions=["X"]),
        Skill(id="B", name="B", preconditions=["X"]),
        Skill(id="lonely", name="lonely",
              preconditions=["nowhere"], postconditions=["nowhere"]),
    ]
    out = predicate_graph_check(skills)
    assert "lonely" in out["isolated_skill_ids"]


def test_payload_shape_complete():
    from verimem.predicate_graph_check import predicate_graph_check

    out = predicate_graph_check([])
    for k in ("has_cycles", "cycles", "n_nodes", "n_edges",
                "isolated_skill_ids"):
        assert k in out


def test_n_edges_count():
    from verimem.predicate_graph_check import predicate_graph_check

    skills = [
        Skill(id="A", name="A", postconditions=["X", "Y"]),
        Skill(id="B", name="B", preconditions=["X"]),
        Skill(id="C", name="C", preconditions=["Y"]),
        Skill(id="D", name="D", preconditions=["Y"]),
    ]
    # A → B (X match), A → C (Y match), A → D (Y match) = 3 edges.
    out = predicate_graph_check(skills)
    assert out["n_edges"] == 3
