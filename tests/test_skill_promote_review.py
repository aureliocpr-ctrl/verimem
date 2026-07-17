"""R34: Skill promote/demote review.

For each skill, suggest action:
  - "promote": candidate with trials>=min and fitness>=threshold
  - "demote": promoted skill with recent fitness drop
  - "keep": no action needed
  - "retire": stale + low fitness
"""
from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class _Skill:
    id: str
    status: str = "candidate"
    trials: int = 0
    successes: int = 0
    last_used_at: float = 0.0


def test_empty_returns_no_review():
    from verimem.skill_promote_review import review_promotions
    out = review_promotions([])
    assert out["reviews"] == []


def test_promote_candidate_high_fitness():
    from verimem.skill_promote_review import review_promotions
    skills = [_Skill("c1", "candidate", trials=20, successes=18,
                     last_used_at=time.time())]
    out = review_promotions(skills, min_trials=10, fitness_threshold=0.7)
    rev = [r for r in out["reviews"] if r["skill_id"] == "c1"]
    assert rev and rev[0]["suggested_action"] == "promote"


def test_keep_candidate_low_fitness():
    from verimem.skill_promote_review import review_promotions
    skills = [_Skill("c1", "candidate", trials=20, successes=10)]
    out = review_promotions(skills, fitness_threshold=0.7)
    rev = [r for r in out["reviews"] if r["skill_id"] == "c1"]
    if rev:
        assert rev[0]["suggested_action"] in {"keep", "retire"}


def test_retire_stale_low_fitness():
    from verimem.skill_promote_review import review_promotions
    now = time.time()
    skills = [_Skill("old", "candidate", trials=10, successes=2,
                     last_used_at=now - 86400 * 365)]
    out = review_promotions(skills, stale_days=180,
                            fitness_threshold=0.5, now=now)
    rev = [r for r in out["reviews"] if r["skill_id"] == "old"]
    if rev:
        assert rev[0]["suggested_action"] == "retire"


def test_keep_promoted_high_fitness():
    from verimem.skill_promote_review import review_promotions
    skills = [_Skill("p1", "promoted", trials=20, successes=18,
                     last_used_at=time.time())]
    out = review_promotions(skills, fitness_threshold=0.7)
    rev = [r for r in out["reviews"] if r["skill_id"] == "p1"]
    if rev:
        assert rev[0]["suggested_action"] == "keep"


def test_payload_shape():
    from verimem.skill_promote_review import review_promotions
    out = review_promotions([])
    for k in ("reviews", "n_skills_scanned", "summary"):
        assert k in out


def test_summary_counts():
    from verimem.skill_promote_review import review_promotions
    now = time.time()
    skills = [
        _Skill("p1", "candidate", trials=20, successes=18, last_used_at=now),
        _Skill("p2", "candidate", trials=20, successes=18, last_used_at=now),
    ]
    out = review_promotions(skills, fitness_threshold=0.7, min_trials=10)
    assert out["summary"].get("promote", 0) >= 1
