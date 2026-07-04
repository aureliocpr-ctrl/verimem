"""R18: Smart pruning — choose which skills to keep under budget.

Score(skill) = ROI(skill) * status_weight * freshness_factor

Where:
  - ROI = fitness * avg_tokens * log(1+trials)
  - status_weight: promoted=2.0, candidate=1.0, retired=0.0
  - freshness_factor: exp decay with 90-day half-life on last_used_at

Algorithm:
  1. Compute score per non-retired skill
  2. Sort desc
  3. Keep top `budget`, prune the rest
"""
from __future__ import annotations

import math
import time
from typing import Any

_DAY_SEC = 86400.0


def _safe_fitness(skill: Any) -> float:
    trials = int(getattr(skill, "trials", 0) or 0)
    successes = int(getattr(skill, "successes", 0) or 0)
    if trials <= 0:
        return 0.0
    return successes / trials


def _freshness(skill: Any, now: float, half_life_days: float) -> float:
    last_used = float(getattr(skill, "last_used_at", 0.0) or 0.0)
    if last_used <= 0:
        return 0.5  # never used: medium freshness
    age_days = max(0.0, (now - last_used) / _DAY_SEC)
    return 0.5 ** (age_days / half_life_days) if half_life_days > 0 else 1.0


def smart_prune(
    skills: list[Any],
    *,
    budget: int,
    now: float | None = None,
    half_life_days: float = 90.0,
    status_weight: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Return {keep, prune} lists under budget."""
    if now is None:
        now = time.time()
    if status_weight is None:
        status_weight = {"promoted": 2.0, "candidate": 1.0, "retired": 0.0}

    scored: list[dict[str, Any]] = []
    for s in skills:
        st = getattr(s, "status", "candidate")
        w = status_weight.get(st, 1.0)
        if w == 0.0:
            continue
        fitness = _safe_fitness(s)
        trials = int(getattr(s, "trials", 0) or 0)
        avg_tokens = float(getattr(s, "avg_tokens", 0.0) or 0.0)
        roi = (fitness * avg_tokens * math.log(1 + trials)
               if trials > 0 else 0.01)
        freshness = _freshness(s, now=now, half_life_days=half_life_days)
        score = roi * w * freshness
        scored.append({
            "id": getattr(s, "id", ""),
            "name": getattr(s, "name", ""),
            "score": round(score, 3),
            "roi": round(roi, 3),
            "status": st,
            "freshness": round(freshness, 3),
        })

    scored.sort(key=lambda e: -e["score"])
    keep = scored[:budget]
    prune = scored[budget:]
    return {
        "keep": keep,
        "prune": prune,
        "budget": budget,
        "n_total": len(skills),
    }


__all__ = ["smart_prune"]
