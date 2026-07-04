"""R12: Skill ROI ranking — rank skills by value-saved-per-use.

ROI = (estimated_tokens_saved * fitness) / (trials)
A skill that fires often (high trials), has high fitness, and replaces
expensive LLM calls (tokens) → high ROI → prioritize keeping it warm.

Useful for:
- Memory budget triage (keep top-ROI under cap, prune rest)
- Compilation prioritization (compile high-ROI candidates first)
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class _Skill:
    id: str
    name: str = "n"
    trials: int = 0
    successes: int = 0
    avg_tokens: float = 0.0
    status: str = "candidate"


def test_empty_returns_empty():
    from engram.skill_roi import rank_skills_by_roi
    out = rank_skills_by_roi([])
    assert out["ranked"] == []


def test_high_roi_skill_first():
    from engram.skill_roi import rank_skills_by_roi
    skills = [
        _Skill("low", trials=2, successes=1, avg_tokens=100),
        _Skill("high", trials=50, successes=45, avg_tokens=2000),
    ]
    out = rank_skills_by_roi(skills)
    assert out["ranked"][0]["id"] == "high"


def test_zero_trials_handled():
    from engram.skill_roi import rank_skills_by_roi
    skills = [_Skill("unused", trials=0, successes=0, avg_tokens=500)]
    out = rank_skills_by_roi(skills)
    # ROI undefined → should be 0 or None
    assert out["ranked"][0]["roi"] in (0.0, None) or out["ranked"][0]["roi"] >= 0


def test_retired_skill_excluded():
    from engram.skill_roi import rank_skills_by_roi
    skills = [
        _Skill("active", trials=10, successes=8, avg_tokens=500,
               status="promoted"),
        _Skill("dead", trials=100, successes=90, avg_tokens=10000,
               status="retired"),
    ]
    out = rank_skills_by_roi(skills)
    ids = [r["id"] for r in out["ranked"]]
    assert "active" in ids
    assert "dead" not in ids


def test_top_k_limit():
    from engram.skill_roi import rank_skills_by_roi
    skills = [
        _Skill(f"s{i}", trials=10, successes=8, avg_tokens=100)
        for i in range(10)
    ]
    out = rank_skills_by_roi(skills, top_k=3)
    assert len(out["ranked"]) == 3


def test_payload_keys():
    from engram.skill_roi import rank_skills_by_roi
    out = rank_skills_by_roi([])
    for k in ("ranked", "n_skills_scanned"):
        assert k in out


def test_entry_keys():
    from engram.skill_roi import rank_skills_by_roi
    skills = [_Skill("s1", trials=5, successes=4, avg_tokens=200)]
    out = rank_skills_by_roi(skills)
    if out["ranked"]:
        for k in ("id", "roi", "fitness", "trials"):
            assert k in out["ranked"][0]
