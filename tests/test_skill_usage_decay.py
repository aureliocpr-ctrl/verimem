"""FORGIA pezzo #264 — Wave 63: skill freshness score.

Exponential decay on last_used_at: score = exp(-(now-last_used)/
half_life). Recent skills score ~1.0, stale skills score ~0.0.
"""
from __future__ import annotations

import time

from verimem.skill import Skill


def test_empty_returns_empty():
    from verimem.skill_usage_decay import usage_decay

    out = usage_decay([])
    assert out["skills"] == []


def test_never_used_zero_score():
    from verimem.skill_usage_decay import usage_decay

    skills = [Skill(id="never", name="never", last_used_at=0.0)]
    out = usage_decay(skills)
    record = out["skills"][0]
    assert record["score"] == 0.0


def test_recent_high_score():
    from verimem.skill_usage_decay import usage_decay

    now = time.time()
    skills = [Skill(id="fresh", name="fresh", last_used_at=now)]
    out = usage_decay(skills, now=now)
    record = out["skills"][0]
    assert record["score"] > 0.99


def test_old_low_score():
    from verimem.skill_usage_decay import usage_decay

    now = time.time()
    skills = [
        Skill(id="old", name="old",
              last_used_at=now - 30 * 86400),  # 30 days ago
    ]
    out = usage_decay(skills, now=now, half_life_days=7)
    record = out["skills"][0]
    # 30/7 ≈ 4.3 half-lives → score ~0.05.
    assert record["score"] < 0.1


def test_sorted_by_score_desc():
    from verimem.skill_usage_decay import usage_decay

    now = time.time()
    skills = [
        Skill(id="old", name="old", last_used_at=now - 30 * 86400),
        Skill(id="fresh", name="fresh", last_used_at=now),
        Skill(id="mid", name="mid", last_used_at=now - 7 * 86400),
    ]
    out = usage_decay(skills, now=now)
    scores = [s["score"] for s in out["skills"]]
    assert scores == sorted(scores, reverse=True)


def test_includes_days_since():
    from verimem.skill_usage_decay import usage_decay

    now = time.time()
    skills = [Skill(id="x", last_used_at=now - 5 * 86400)]
    out = usage_decay(skills, now=now)
    rec = out["skills"][0]
    assert abs(rec["days_since"] - 5.0) < 0.1


def test_top_k_respected():
    from verimem.skill_usage_decay import usage_decay

    now = time.time()
    skills = [Skill(id=f"s{i}", last_used_at=now) for i in range(10)]
    out = usage_decay(skills, top_k=3)
    assert len(out["skills"]) == 3


def test_payload_shape_complete():
    from verimem.skill_usage_decay import usage_decay

    out = usage_decay([])
    for k in ("skills", "n_total", "half_life_days"):
        assert k in out
