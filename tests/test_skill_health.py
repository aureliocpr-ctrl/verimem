"""FORGIA pezzo #216 — Wave 15: per-skill health diagnostic.

For each skill, produces a structured report:
  - fitness: mean, lower-bound (5%), variance (Beta posterior)
  - trials, successes, status
  - recency: days since last_used_at, uses in last `days_window`
  - suggested_action: promote / retire / test / pin / ok
  - reasoning: 1-line explanation

The suggested_action implements the curation policy HippoAgent
already uses internally (consolidate phase) but exposes it as a
queryable tool, so the user can ask "what should I do with skill X?"
mid-session.

Action policy (ranked by precedence):
  1. trials==0  → "test" (no signal yet)
  2. status==candidate AND trials>=5 AND fitness_lower_bound>=0.6
     → "promote"
  3. status==promoted AND trials>=10 AND fitness_mean<0.3
     → "retire"
  4. fitness_variance>0.05 AND trials<10
     → "test" (high uncertainty, gather more data)
  5. status==promoted AND trials>=20 AND fitness_mean>=0.85
     → "pin" (top performer, lock in)
  6. Otherwise → "ok"

Six invariants:
  1. unknown action returns "ok" by default.
  2. trials=0 → suggest "test".
  3. high fitness candidate → "promote".
  4. low fitness promoted → "retire".
  5. very high fitness promoted → "pin".
  6. high variance → "test".
"""
from __future__ import annotations

import time

from verimem.skill import Skill


def test_zero_trials_suggests_test():
    from verimem.skill_health import skill_health

    s = Skill(id="s", name="s", trials=0, successes=0, status="candidate")
    out = skill_health(s, episodes=[])
    assert out["suggested_action"] == "test"


def test_candidate_with_high_fitness_suggests_promote():
    from verimem.skill_health import skill_health

    # 9/10 → fitness_mean ~0.83, lower bound ~0.59 with default prior.
    # We need lower_bound >= 0.6, so use higher counts.
    s = Skill(id="s", name="s", trials=20, successes=18, status="candidate")
    out = skill_health(s, episodes=[])
    assert out["suggested_action"] == "promote", (
        f"got {out['suggested_action']}; reasoning={out['reasoning']}"
    )


def test_promoted_low_fitness_suggests_retire():
    from verimem.skill_health import skill_health

    s = Skill(id="s", name="s", trials=30, successes=5, status="promoted")
    out = skill_health(s, episodes=[])
    assert out["suggested_action"] == "retire"


def test_top_performer_promoted_suggests_pin():
    from verimem.skill_health import skill_health

    s = Skill(id="s", name="s", trials=30, successes=29, status="promoted")
    out = skill_health(s, episodes=[])
    assert out["suggested_action"] == "pin"


def test_high_variance_suggests_test():
    from verimem.skill_health import skill_health

    # trials=1, successes=0: Beta(1+0, 1+1) = Beta(1, 2)
    # variance = 1*2 / (3^2 * 4) = 2/36 ≈ 0.0556 > 0.05.
    # Few trials and high uncertainty should recommend more testing.
    s = Skill(id="s", name="s", trials=1, successes=0, status="candidate")
    out = skill_health(s, episodes=[])
    assert out["suggested_action"] == "test"


def test_payload_shape_complete():
    from verimem.skill_health import skill_health

    s = Skill(id="s", name="s", trials=10, successes=5)
    out = skill_health(s, episodes=[])
    for key in ("id", "name", "status", "fitness",
                "trials", "successes", "recency",
                "suggested_action", "reasoning"):
        assert key in out
    for fk in ("mean", "lower_bound", "variance"):
        assert fk in out["fitness"]


def test_recency_zero_when_never_used():
    from verimem.skill_health import skill_health

    s = Skill(id="s", name="s", trials=0, successes=0, last_used_at=0.0)
    out = skill_health(s, episodes=[])
    assert out["recency"]["days_since_last_use"] is None or \
        out["recency"]["days_since_last_use"] > 365 * 30


def test_recency_recent_use():
    from verimem.skill_health import skill_health

    s = Skill(id="s", name="s", trials=10, successes=8,
              last_used_at=time.time() - 3600)  # 1h ago
    out = skill_health(s, episodes=[])
    assert out["recency"]["days_since_last_use"] is not None
    assert out["recency"]["days_since_last_use"] < 1.0


def test_reasoning_is_explanatory():
    from verimem.skill_health import skill_health

    s = Skill(id="s", name="s", trials=20, successes=18, status="candidate")
    out = skill_health(s, episodes=[])
    # Reasoning must be a non-empty string.
    assert isinstance(out["reasoning"], str)
    assert len(out["reasoning"]) > 5
