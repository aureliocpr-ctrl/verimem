"""R26: Skill combo mining — pairs of skills frequently used together.

For each pair (A, B) of skills, count co-occurrences in
episodes.skills_used. Pairs above min_cooccurrence are returned
with success_rate (success / total co-occurrences).

These pairs are candidates for super-skill compilation (R12+R6
chain that compose_macro could fuse).
"""
from __future__ import annotations

from collections import defaultdict
from itertools import combinations
from typing import Any


def mine_skill_combos(
    episodes: list[Any],
    *,
    min_cooccurrence: int = 3,
    top_k: int = 50,
) -> dict[str, Any]:
    """Mine frequently co-occurring skill pairs."""
    if not episodes:
        return {"combos": [], "n_episodes_scanned": 0}

    pair_count: dict[tuple[str, str], int] = defaultdict(int)
    pair_success: dict[tuple[str, str], int] = defaultdict(int)

    for ep in episodes:
        skills = sorted(set(getattr(ep, "skills_used", []) or []))
        outcome = getattr(ep, "outcome", "")
        for a, b in combinations(skills, 2):
            key = (a, b)
            pair_count[key] += 1
            if outcome == "success":
                pair_success[key] += 1

    combos: list[dict[str, Any]] = []
    for (a, b), n in pair_count.items():
        if n < min_cooccurrence:
            continue
        n_succ = pair_success.get((a, b), 0)
        rate = n_succ / n if n else 0.0
        combos.append({
            "pair": [a, b],
            "count": n,
            "success_rate": round(rate, 3),
            "n_success": n_succ,
        })

    combos.sort(key=lambda c: (-c["count"], -c["success_rate"]))

    return {
        "combos": combos[:top_k],
        "n_episodes_scanned": len(episodes),
    }


__all__ = ["mine_skill_combos"]
