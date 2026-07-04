"""R12: Skill ROI ranking — value-saved-per-use.

ROI = fitness * avg_tokens * log(1 + trials)

Rationale:
- High `avg_tokens` → skill replaces an expensive LLM call → high value
- High `fitness` → skill actually works → low risk
- `log(1 + trials)` → reward usage but with diminishing returns
  (one-shot wonders rank lower than steadily-used skills)

Retired skills excluded. Candidates included (early signal).
"""
from __future__ import annotations

import math
from typing import Any


def _safe_fitness(skill: Any) -> float:
    trials = int(getattr(skill, "trials", 0) or 0)
    successes = int(getattr(skill, "successes", 0) or 0)
    if trials <= 0:
        return 0.0
    return successes / trials


def rank_skills_by_roi(
    skills: list[Any],
    *,
    top_k: int = 50,
) -> dict[str, Any]:
    """Rank skills by ROI desc. Returns ranked list + scan count."""
    ranked: list[dict[str, Any]] = []
    for s in skills:
        if getattr(s, "status", "") == "retired":
            continue
        fitness = _safe_fitness(s)
        trials = int(getattr(s, "trials", 0) or 0)
        avg_tokens = float(getattr(s, "avg_tokens", 0.0) or 0.0)
        roi = fitness * avg_tokens * math.log(1 + trials) if trials > 0 else 0.0
        ranked.append({
            "id": getattr(s, "id", ""),
            "name": getattr(s, "name", ""),
            "roi": round(roi, 2),
            "fitness": round(fitness, 3),
            "trials": trials,
            "avg_tokens": round(avg_tokens, 1),
            "status": getattr(s, "status", ""),
        })
    ranked.sort(key=lambda r: -r["roi"])
    return {
        "ranked": ranked[:top_k],
        "n_skills_scanned": len(skills),
    }


__all__ = ["rank_skills_by_roi"]
