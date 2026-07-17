"""FORGIA pezzo #220 — Wave 19: batch skill_health, grouped by
suggested_action. Curation dashboard in one call.

The user can ask "which skills need attention?" and get a clear
breakdown:
  - promote: 5 candidates ready to graduate
  - retire: 3 promoted underperforming
  - test: 8 high-uncertainty skills
  - pin: 2 top performers
  - ok: 17 healthy

Each group is ranked by relevance (highest fitness first within
promote/pin; lowest fitness first within retire; highest variance
first within test).
"""
from __future__ import annotations

from verimem.skill import Skill


def _make_pool() -> list[Skill]:
    return [
        # Promote candidates (high fitness, candidate, ≥5 trials).
        Skill(id="p1", name="ready_alpha", trials=20, successes=18,
              status="candidate"),
        Skill(id="p2", name="ready_beta", trials=15, successes=14,
              status="candidate"),
        # Retire candidates (low fitness, promoted, ≥10 trials).
        Skill(id="r1", name="failing_one", trials=20, successes=2,
              status="promoted"),
        # Pin candidate (very high fitness, promoted, ≥20 trials).
        Skill(id="pin1", name="top_perf", trials=30, successes=29,
              status="promoted"),
        # Test (zero trials).
        Skill(id="t1", name="never_run", trials=0, successes=0,
              status="candidate"),
        # OK.
        Skill(id="o1", name="middle_of_road", trials=10, successes=5,
              status="promoted"),
    ]


def test_groups_by_action():
    from verimem.recommend_actions import recommend_actions

    out = recommend_actions(_make_pool())
    actions = out["actions"]
    assert "promote" in actions
    assert "retire" in actions
    assert "test" in actions
    assert "pin" in actions
    assert "ok" in actions
    promote_ids = {x["id"] for x in actions["promote"]}
    retire_ids = {x["id"] for x in actions["retire"]}
    pin_ids = {x["id"] for x in actions["pin"]}
    assert "p1" in promote_ids
    assert "p2" in promote_ids
    assert "r1" in retire_ids
    assert "pin1" in pin_ids


def test_promote_group_ranked_by_fitness_desc():
    from verimem.recommend_actions import recommend_actions

    out = recommend_actions(_make_pool())
    promote = out["actions"]["promote"]
    fitnesses = [s["fitness_mean"] for s in promote]
    assert fitnesses == sorted(fitnesses, reverse=True)


def test_retire_group_ranked_by_fitness_asc():
    """Retire candidates ranked worst-first."""
    from verimem.recommend_actions import recommend_actions

    pool = [
        Skill(id="r1", name="r1", trials=20, successes=4, status="promoted"),
        Skill(id="r2", name="r2", trials=20, successes=2, status="promoted"),
        Skill(id="r3", name="r3", trials=20, successes=5, status="promoted"),
    ]
    out = recommend_actions(pool)
    retire = out["actions"]["retire"]
    fitnesses = [s["fitness_mean"] for s in retire]
    assert fitnesses == sorted(fitnesses)


def test_summary_string_present():
    from verimem.recommend_actions import recommend_actions

    out = recommend_actions(_make_pool())
    assert isinstance(out["summary"], str)
    assert len(out["summary"]) > 5


def test_n_total_matches_input_size():
    from verimem.recommend_actions import recommend_actions

    pool = _make_pool()
    out = recommend_actions(pool)
    assert out["n_total"] == len(pool)


def test_empty_library_returns_empty_groups():
    from verimem.recommend_actions import recommend_actions

    out = recommend_actions([])
    assert out["n_total"] == 0
    for group in out["actions"].values():
        assert group == []


def test_top_k_per_group_respected():
    """top_k caps each group's size."""
    from verimem.recommend_actions import recommend_actions

    # 5 promote candidates, top_k_per_group=2 → only 2 in promote.
    pool = [
        Skill(id=f"p{i}", name=f"ready{i}", trials=20, successes=19,
              status="candidate")
        for i in range(5)
    ]
    out = recommend_actions(pool, top_k_per_group=2)
    assert len(out["actions"]["promote"]) == 2


def test_payload_shape_complete():
    from verimem.recommend_actions import recommend_actions

    out = recommend_actions([])
    for key in ("summary", "n_total", "actions"):
        assert key in out
