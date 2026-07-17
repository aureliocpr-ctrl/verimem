"""Per-skill path analysis: predecessors and successors.

FORGIA pezzo #234 — Wave 33. Focused view of transition stats
around ONE skill: who tends to come before, who tends to come after.
"""
from __future__ import annotations

from collections import Counter
from typing import Any


def skill_path(
    *,
    skill_id: str,
    episodes: list[Any],
    top_k: int = 5,
) -> dict[str, Any]:
    """Compute predecessor + successor distributions for `skill_id`.

    Args:
      - `skill_id`: target skill.
      - `episodes`: iterable of episode-likes with `skills_used`.
      - `top_k`: cap on each list.

    Returns: `{skill_id, n_total_appearances, predecessors,
    successors}` where each predecessor/successor is `{skill_id,
    count, fraction}` sorted by count DESC.
    """
    n_appearances = 0
    pre_counts: Counter[str] = Counter()
    suc_counts: Counter[str] = Counter()

    for ep in episodes:
        seq = getattr(ep, "skills_used", None) or []
        for i, cur in enumerate(seq):
            if cur != skill_id:
                continue
            n_appearances += 1
            # Predecessor (immediate).
            if i > 0 and seq[i - 1] != skill_id:
                pre_counts[seq[i - 1]] += 1
            # Successor (immediate).
            if i + 1 < len(seq) and seq[i + 1] != skill_id:
                suc_counts[seq[i + 1]] += 1

    def _to_records(counter: Counter[str]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for sid, c in counter.most_common(top_k):
            rows.append({
                "skill_id": sid,
                "count": c,
                "fraction": c / n_appearances if n_appearances > 0 else 0.0,
            })
        return rows

    return {
        "skill_id": skill_id,
        "n_total_appearances": n_appearances,
        "predecessors": _to_records(pre_counts),
        "successors": _to_records(suc_counts),
    }


__all__ = ["skill_path"]
