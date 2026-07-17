"""Batch duplicate-skill detection.

FORGIA pezzo #232 — Wave 31. Sweeps the full skill library for
ALL pairs above a Jaccard threshold on the token signature.
Returns ranked candidates the user can manually merge or
automatically dedupe.
"""
from __future__ import annotations

import re
from itertools import combinations
from typing import Any

from .skill import Skill

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _signature(s: Skill) -> set[str]:
    parts = [
        s.name or "", s.trigger or "", s.body or "",
        " ".join(s.preconditions or []),
        " ".join(s.postconditions or []),
    ]
    return set(_TOKEN_RE.findall(" ".join(parts).lower()))


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    union = len(a | b)
    return len(a & b) / union if union > 0 else 0.0


def find_duplicate_skills(
    skills: list[Skill],
    *,
    threshold: float = 0.8,
    top_k: int = 50,
) -> dict[str, Any]:
    """Find all skill pairs with Jaccard ≥ threshold.

    Args:
      - `skills`: full skill pool.
      - `threshold`: minimum Jaccard for a pair to be reported.
      - `top_k`: cap on returned pairs.

    Returns: `{n_total_skills, threshold, pairs}` where each pair
    is `{skill_a, skill_b, name_a, name_b, jaccard}` sorted by
    Jaccard DESC.

    Complexity: O(S²) on signature comparison. For S ≤ 1000 this
    is well under a second.
    """
    sigs = [(s, _signature(s)) for s in skills]
    pairs: list[dict[str, Any]] = []
    for (a, sa), (b, sb) in combinations(sigs, 2):
        j = _jaccard(sa, sb)
        if j >= threshold:
            pairs.append({
                "skill_a": a.id, "skill_b": b.id,
                "name_a": a.name, "name_b": b.name,
                "jaccard": j,
            })
    pairs.sort(key=lambda p: -p["jaccard"])
    return {
        "n_total_skills": len(skills),
        "threshold": threshold,
        "pairs": pairs[:top_k],
    }


__all__ = ["find_duplicate_skills"]
