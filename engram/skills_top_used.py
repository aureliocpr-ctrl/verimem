"""Top-used skills by episode count.

FORGIA pezzo #274 — Wave 73. Counts episodes per skill (dedup
within episode). Useful per 'workhorse' skills.
"""
from __future__ import annotations

from collections import Counter
from typing import Any


def top_used_skills(
    *,
    episodes: list[Any],
    top_k: int = 20,
) -> dict[str, Any]:
    """Count distinct episodes per skill, return top N."""
    counts: Counter[str] = Counter()
    for ep in episodes:
        used = set(getattr(ep, "skills_used", None) or [])
        for sid in used:
            counts[sid] += 1
    records = [
        {"skill_id": sid, "n_episodes": n}
        for sid, n in counts.most_common(top_k)
    ]
    return {
        "n_unique_skills": len(counts),
        "skills": records,
    }


__all__ = ["top_used_skills"]
