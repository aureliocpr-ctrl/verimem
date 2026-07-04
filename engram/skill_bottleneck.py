"""R20: Find skill bottlenecks.

A skill is a bottleneck when:
  - status == 'candidate' (not yet promoted)
  - fitness < max_fitness_threshold
  - has >= min_blocked_children non-promoted children

These are the highest-leverage skills to fix: unblocking them
unlocks a downstream cascade.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any


def find_bottlenecks(
    skills: list[Any],
    *,
    min_blocked_children: int = 2,
    max_fitness_threshold: float = 0.5,
    top_k: int = 50,
) -> dict[str, Any]:
    """Identify high-leverage skill bottlenecks."""
    if not skills:
        return {"bottlenecks": [], "n_total_skills": 0}

    children_of: dict[str, list[str]] = defaultdict(list)
    for s in skills:
        for p in getattr(s, "parent_skills", []) or []:
            if getattr(s, "status", "") != "promoted":
                children_of[p].append(getattr(s, "id", ""))

    bottlenecks: list[dict[str, Any]] = []
    for s in skills:
        if getattr(s, "status", "") != "candidate":
            continue
        sid = getattr(s, "id", "")
        trials = int(getattr(s, "trials", 0) or 0)
        successes = int(getattr(s, "successes", 0) or 0)
        fitness = (successes / trials) if trials > 0 else 0.0
        if fitness > max_fitness_threshold:
            continue
        blocked = children_of.get(sid, [])
        if len(blocked) < min_blocked_children:
            continue
        bottlenecks.append({
            "skill_id": sid,
            "name": getattr(s, "name", ""),
            "fitness": round(fitness, 3),
            "trials": trials,
            "n_blocked_children": len(blocked),
            "blocked_child_ids": blocked[:10],
            "rationale": (
                f"fitness={fitness:.2f} (≤{max_fitness_threshold}) "
                f"and {len(blocked)} child skills can't promote"
            ),
        })

    bottlenecks.sort(key=lambda b: -b["n_blocked_children"])
    return {
        "bottlenecks": bottlenecks[:top_k],
        "n_total_skills": len(skills),
    }


__all__ = ["find_bottlenecks"]
