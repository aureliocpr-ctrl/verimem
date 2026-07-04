"""FORGIA pezzo #275 — Wave 74: per-stage skill aggregate stats."""
from __future__ import annotations

from engram.skill import Skill


def test_empty():
    from engram.skills_aggregate_stats import aggregate_stats

    out = aggregate_stats([])
    assert out["by_stage"] == {}


def test_by_stage_counts():
    from engram.skills_aggregate_stats import aggregate_stats

    skills = [
        Skill(id="a", stage="nrem"),
        Skill(id="b", stage="nrem"),
        Skill(id="c", stage="rem"),
        Skill(id="d", stage="schema"),
    ]
    out = aggregate_stats(skills)
    assert out["by_stage"]["nrem"]["count"] == 2
    assert out["by_stage"]["rem"]["count"] == 1
    assert out["by_stage"]["schema"]["count"] == 1


def test_by_status_counts():
    from engram.skills_aggregate_stats import aggregate_stats

    skills = [
        Skill(id="a", status="candidate"),
        Skill(id="b", status="promoted"),
        Skill(id="c", status="retired"),
        Skill(id="d", status="promoted"),
    ]
    out = aggregate_stats(skills)
    assert out["by_status"]["candidate"] == 1
    assert out["by_status"]["promoted"] == 2
    assert out["by_status"]["retired"] == 1


def test_avg_fitness_per_stage():
    from engram.skills_aggregate_stats import aggregate_stats

    skills = [
        Skill(id="a", stage="nrem", trials=10, successes=8),
        Skill(id="b", stage="nrem", trials=10, successes=4),
    ]
    out = aggregate_stats(skills)
    # nrem avg fitness: mean of (0.75, 0.42) ≈ 0.58.
    assert 0.4 < out["by_stage"]["nrem"]["avg_fitness"] < 0.7


def test_overall_counts():
    from engram.skills_aggregate_stats import aggregate_stats

    skills = [Skill(id=f"s{i}") for i in range(5)]
    out = aggregate_stats(skills)
    assert out["n_total"] == 5


def test_payload_shape():
    from engram.skills_aggregate_stats import aggregate_stats

    out = aggregate_stats([])
    for k in ("n_total", "by_stage", "by_status"):
        assert k in out
