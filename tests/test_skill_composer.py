"""R10: Skill Composer — auto-plan a multi-skill chain.

Given a new task and a library of skills (each with trigger/body),
identify which skills can chain to solve it. Returns a proposed plan
as a sequence of skill_ids.

Algorithm:
1. Match task tokens against each skill.trigger (Jaccard).
2. Build a dependency graph from parent_skills.
3. Greedy chain: start from highest-matching skill, follow parents.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class _Skill:
    id: str
    trigger: str
    body: str = ""
    parent_skills: list[str] = field(default_factory=list)
    status: str = "promoted"
    fitness_mean: float = 0.8
    trials: int = 10


def test_empty_returns_no_plan():
    from verimem.skill_composer import compose_plan

    out = compose_plan(task="any task", skills=[])
    assert out["plan"] == []
    assert out["coverage"] == 0.0


def test_single_match_returns_plan():
    from verimem.skill_composer import compose_plan

    skills = [
        _Skill("s1", "WordPress contact-form-7 RCE",
               body="exploit CVE-2023-6449"),
    ]
    out = compose_plan(
        task="target acme.io WordPress contact-form-7 exploitation",
        skills=skills,
    )
    assert "s1" in [p["skill_id"] for p in out["plan"]]


def test_chain_follows_parents():
    from verimem.skill_composer import compose_plan

    skills = [
        _Skill("recon", "WordPress fingerprint"),
        _Skill("exploit", "WordPress RCE",
               parent_skills=["recon"]),
    ]
    out = compose_plan(task="WordPress RCE attack", skills=skills)
    plan_ids = [p["skill_id"] for p in out["plan"]]
    # Should include both recon (parent) AND exploit
    assert "recon" in plan_ids
    assert "exploit" in plan_ids
    # Parents BEFORE children in plan order
    assert plan_ids.index("recon") < plan_ids.index("exploit")


def test_no_match_returns_empty():
    from verimem.skill_composer import compose_plan

    skills = [_Skill("s1", "completely unrelated topic")]
    out = compose_plan(task="WordPress exploitation", skills=skills)
    assert out["plan"] == []


def test_retired_skills_excluded():
    from verimem.skill_composer import compose_plan

    skills = [
        _Skill("s1", "WordPress RCE", status="retired"),
        _Skill("s2", "WordPress RCE", status="promoted"),
    ]
    out = compose_plan(task="WordPress RCE", skills=skills)
    plan_ids = [p["skill_id"] for p in out["plan"]]
    assert "s1" not in plan_ids
    assert "s2" in plan_ids


def test_coverage_score():
    from verimem.skill_composer import compose_plan

    skills = [
        _Skill("s1", "WordPress RCE exploit chain"),
    ]
    out = compose_plan(task="WordPress RCE", skills=skills)
    assert 0.0 < out["coverage"] <= 1.0


def test_payload_keys():
    from verimem.skill_composer import compose_plan
    out = compose_plan(task="x", skills=[])
    for k in ("plan", "coverage", "n_skills_scanned", "n_skills_matched"):
        assert k in out


def test_plan_includes_match_score():
    from verimem.skill_composer import compose_plan

    skills = [_Skill("s1", "WordPress RCE")]
    out = compose_plan(task="WordPress RCE", skills=skills)
    if out["plan"]:
        assert "match_score" in out["plan"][0]
        assert 0.0 <= out["plan"][0]["match_score"] <= 1.0
