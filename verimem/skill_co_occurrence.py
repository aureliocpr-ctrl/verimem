"""Symmetric skill co-occurrence matrix.

FORGIA pezzo #225 — Wave 24. Counts pairs of skills that appear in
the SAME episode (order-independent), with Jaccard similarity over
episode sets. Different signal from SR transitions (asymmetric,
ordered): this captures "tend to be used together".
"""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from .skill import Skill


def skill_co_occurrence(
    *,
    skills: list[Skill],
    episodes: list[Any],
    top_pairs: int = 20,
) -> dict[str, Any]:
    """Compute the symmetric skill co-occurrence + Jaccard.

    Args:
      - `skills`: skill pool (only these are considered).
      - `episodes`: iterable of episode-likes with `skills_used`.
      - `top_pairs`: cap on returned pairs (sorted by count DESC).

    Returns: `{n_episodes, n_skills, pairs}` where each pair is
    `{skill_a, skill_b, count, jaccard}`.
    """
    skill_ids = {s.id for s in skills}

    pair_count: Counter[tuple[str, str]] = Counter()
    presence: defaultdict[str, set[int]] = defaultdict(set)

    for i, ep in enumerate(episodes):
        used = {s for s in (getattr(ep, "skills_used", None) or [])
                if s in skill_ids}
        for s in used:
            presence[s].add(i)
        items = sorted(used)
        for a_idx in range(len(items)):
            for b_idx in range(a_idx + 1, len(items)):
                a, b = items[a_idx], items[b_idx]
                pair_count[(a, b)] += 1

    pairs: list[dict[str, Any]] = []
    for (a, b), count in pair_count.items():
        union = len(presence[a] | presence[b])
        jaccard = count / union if union > 0 else 0.0
        pairs.append({
            "skill_a": a,
            "skill_b": b,
            "count": count,
            "jaccard": jaccard,
        })

    pairs.sort(key=lambda p: -p["count"])
    return {
        "n_episodes": len(episodes),
        "n_skills": len(skills),
        "pairs": pairs[:top_pairs],
    }


__all__ = ["skill_co_occurrence"]
