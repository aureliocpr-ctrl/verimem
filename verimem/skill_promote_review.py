"""R34: Skill promote/demote/retire review.

For each skill, suggest one of:
  - promote: candidate skill ready for promotion (trials, fitness OK)
  - demote: promoted with recent low fitness (handled by drift)
  - retire: stale (no use for X days) + low fitness
  - keep: no action

Pure-local, deterministic. Designed as advisor — actual action up
to the user / consolidation cycle.
"""
from __future__ import annotations

import time
from collections import Counter
from typing import Any


def review_promotions(
    skills: list[Any],
    *,
    now: float | None = None,
    min_trials: int = 5,
    fitness_threshold: float = 0.7,
    stale_days: float = 180.0,
    top_k: int = 200,
) -> dict[str, Any]:
    """Suggest action per skill."""
    if now is None:
        now = time.time()
    reviews: list[dict[str, Any]] = []
    summary: Counter = Counter()

    for s in skills:
        sid = getattr(s, "id", "")
        status = getattr(s, "status", "candidate")
        if status == "retired":
            continue  # already done
        trials = int(getattr(s, "trials", 0) or 0)
        successes = int(getattr(s, "successes", 0) or 0)
        fitness = (successes / trials) if trials > 0 else 0.0
        last_used = float(getattr(s, "last_used_at", 0.0) or 0.0)
        age_days = (now - last_used) / 86400.0 if last_used > 0 else 9999.0

        action = "keep"
        rationale = ""
        if status == "candidate":
            if (trials >= min_trials
                    and fitness >= fitness_threshold):
                action = "promote"
                rationale = (
                    f"candidate has {trials} trials, fitness="
                    f"{fitness:.2f} ≥ {fitness_threshold}"
                )
            elif (age_days >= stale_days and fitness < 0.5
                    and trials > 0):
                action = "retire"
                rationale = (
                    f"stale ({age_days:.0f}d) and low fitness "
                    f"({fitness:.2f})"
                )
            else:
                action = "keep"
                rationale = "not yet eligible for promotion"
        elif status == "promoted":
            if age_days >= stale_days and fitness < 0.5:
                action = "retire"
                rationale = (
                    f"promoted but stale ({age_days:.0f}d) "
                    f"and fitness dropped ({fitness:.2f})"
                )
            else:
                action = "keep"
                rationale = "promoted and healthy"

        reviews.append({
            "skill_id": sid,
            "current_status": status,
            "suggested_action": action,
            "fitness": round(fitness, 3),
            "trials": trials,
            "age_days": round(age_days, 1) if age_days < 9999 else None,
            "rationale": rationale,
        })
        summary[action] += 1

    return {
        "reviews": reviews[:top_k],
        "n_skills_scanned": len(skills),
        "summary": dict(summary),
    }


__all__ = ["review_promotions"]
