"""R19: Success factor analysis — correlate skills with outcomes.

For each skill that appears in past episodes, compute:
  - n_uses: total times it was used
  - n_success: episodes with outcome=success that used it
  - success_rate = n_success / n_uses

Skills below `min_uses` are filtered out (statistical noise).
Output: sorted by success_rate desc, ties broken by n_uses desc.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any


def analyze_success_factors(
    episodes: list[Any],
    *,
    min_uses: int = 3,
    top_k: int = 100,
) -> dict[str, Any]:
    """Per skill, compute success rate from past episodes."""
    uses: dict[str, int] = defaultdict(int)
    successes: dict[str, int] = defaultdict(int)

    for ep in episodes:
        outcome = getattr(ep, "outcome", "")
        skills = getattr(ep, "skills_used", []) or []
        for s in skills:
            uses[s] += 1
            if outcome == "success":
                successes[s] += 1

    factors: list[dict[str, Any]] = []
    for sid, n_uses in uses.items():
        if n_uses < min_uses:
            continue
        n_succ = successes.get(sid, 0)
        rate = n_succ / n_uses if n_uses else 0.0
        factors.append({
            "skill_id": sid,
            "n_uses": n_uses,
            "n_success": n_succ,
            "success_rate": round(rate, 3),
        })

    factors.sort(key=lambda f: (-f["success_rate"], -f["n_uses"]))

    return {
        "factors": factors[:top_k],
        "n_episodes_scanned": len(episodes),
        "n_unique_skills": len(uses),
    }


__all__ = ["analyze_success_factors"]
