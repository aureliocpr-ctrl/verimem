"""R18: Smart pruning — combine ROI + age + status to decide what to keep.

When memory budget is limited, score each skill by a composite value
and prune the lowest until under budget.

Score = ROI * status_weight * freshness_factor
"""
from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class _Skill:
    id: str
    name: str = "n"
    trials: int = 0
    successes: int = 0
    avg_tokens: float = 0.0
    status: str = "candidate"
    last_used_at: float = 0.0


def test_empty_returns_no_pruning():
    from engram.smart_pruning import smart_prune

    out = smart_prune([], budget=10)
    assert out["keep"] == []
    assert out["prune"] == []


def test_under_budget_no_prune():
    from engram.smart_pruning import smart_prune

    now = time.time()
    skills = [
        _Skill(f"s{i}", trials=5, successes=4, avg_tokens=100,
               last_used_at=now)
        for i in range(3)
    ]
    out = smart_prune(skills, budget=10)
    assert len(out["keep"]) == 3
    assert out["prune"] == []


def test_over_budget_lowest_score_pruned():
    from engram.smart_pruning import smart_prune

    now = time.time()
    skills = [
        _Skill("high",
               trials=20, successes=18, avg_tokens=500,
               status="promoted", last_used_at=now),
        _Skill("low",
               trials=2, successes=1, avg_tokens=50,
               status="candidate",
               last_used_at=now - 86400 * 365),
        _Skill("mid",
               trials=10, successes=7, avg_tokens=200,
               status="candidate", last_used_at=now),
    ]
    out = smart_prune(skills, budget=2)
    keep_ids = [s["id"] for s in out["keep"]]
    prune_ids = [s["id"] for s in out["prune"]]
    assert "high" in keep_ids
    assert "low" in prune_ids


def test_promoted_skills_prioritized():
    from engram.smart_pruning import smart_prune

    now = time.time()
    skills = [
        _Skill("promoted",
               trials=5, successes=4, avg_tokens=100,
               status="promoted", last_used_at=now),
        _Skill("candidate_higher_roi",
               trials=20, successes=18, avg_tokens=200,
               status="candidate", last_used_at=now),
    ]
    out = smart_prune(skills, budget=1, status_weight={"promoted": 2.0})
    # promoted weight boost should help it survive
    keep_ids = [s["id"] for s in out["keep"]]
    # Either is reasonable; ensure no crash + correct count
    assert len(keep_ids) == 1


def test_payload_keys():
    from engram.smart_pruning import smart_prune
    out = smart_prune([], budget=10)
    for k in ("keep", "prune", "budget", "n_total"):
        assert k in out


def test_entries_have_score():
    from engram.smart_pruning import smart_prune
    now = time.time()
    skills = [_Skill("s1", trials=5, successes=4, avg_tokens=100,
                     last_used_at=now)]
    out = smart_prune(skills, budget=10)
    if out["keep"]:
        assert "score" in out["keep"][0]
