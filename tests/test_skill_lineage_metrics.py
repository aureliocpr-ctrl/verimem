"""R39: Skill lineage graph metrics.

Different from skills_topology: focused on lineage-specific stats
(depth distribution, fanout per node, longest path).
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class _Skill:
    id: str
    parent_skills: list[str] = field(default_factory=list)
    status: str = "candidate"


def test_empty_returns_zero():
    from verimem.skill_lineage_metrics import compute_lineage_metrics
    out = compute_lineage_metrics([])
    assert out["max_depth"] == 0
    assert out["n_roots"] == 0


def test_single_root():
    from verimem.skill_lineage_metrics import compute_lineage_metrics
    skills = [_Skill("root")]
    out = compute_lineage_metrics(skills)
    assert out["n_roots"] == 1
    assert out["max_depth"] == 0


def test_depth_increments_with_chain():
    from verimem.skill_lineage_metrics import compute_lineage_metrics
    skills = [
        _Skill("a"),
        _Skill("b", parent_skills=["a"]),
        _Skill("c", parent_skills=["b"]),
    ]
    out = compute_lineage_metrics(skills)
    assert out["max_depth"] == 2  # a→b→c, c at depth 2


def test_fanout_per_node():
    from verimem.skill_lineage_metrics import compute_lineage_metrics
    skills = [
        _Skill("root"),
        _Skill("c1", parent_skills=["root"]),
        _Skill("c2", parent_skills=["root"]),
        _Skill("c3", parent_skills=["root"]),
    ]
    out = compute_lineage_metrics(skills)
    assert out["max_fanout"] == 3
    assert out["avg_fanout"] > 0


def test_n_leaves():
    from verimem.skill_lineage_metrics import compute_lineage_metrics
    skills = [
        _Skill("a"),
        _Skill("b", parent_skills=["a"]),
        _Skill("c", parent_skills=["a"]),
    ]
    out = compute_lineage_metrics(skills)
    assert out["n_leaves"] == 2


def test_payload_keys():
    from verimem.skill_lineage_metrics import compute_lineage_metrics
    out = compute_lineage_metrics([])
    for k in ("max_depth", "n_roots", "n_leaves", "max_fanout",
              "avg_fanout", "n_total"):
        assert k in out
