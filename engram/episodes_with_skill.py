"""Filter episodes by skill + optional outcome.

FORGIA pezzo #262 — Wave 61. Companion to episodes_by_skill with
explicit outcome filter and total stats for the filtered subset.
"""
from __future__ import annotations

from typing import Any


def episodes_with_skill(
    *,
    skill_id: str,
    episodes: list[Any],
    outcome: str | None = None,
    top_k: int = 20,
) -> dict[str, Any]:
    """Filter episodes that use `skill_id`, sorted recent-first."""
    matched: list[Any] = []
    n_success = 0
    n_failure = 0
    for ep in episodes:
        used = set(getattr(ep, "skills_used", None) or [])
        if skill_id not in used:
            continue
        ep_outcome = getattr(ep, "outcome", "")
        if outcome is not None and ep_outcome != outcome:
            continue
        matched.append(ep)
        if ep_outcome == "success":
            n_success += 1
        elif ep_outcome == "failure":
            n_failure += 1

    matched.sort(
        key=lambda e: -float(getattr(e, "created_at", 0.0) or 0.0),
    )

    records = [
        {
            "id": getattr(e, "id", ""),
            "task_text": (getattr(e, "task_text", "") or "")[:200],
            "outcome": getattr(e, "outcome", ""),
            "created_at": float(getattr(e, "created_at", 0.0) or 0.0),
        }
        for e in matched[:top_k]
    ]

    return {
        "skill_id": skill_id,
        "n_total": len(matched),
        "n_success": n_success,
        "n_failure": n_failure,
        "episodes": records,
        "outcome_filter": outcome,
    }


__all__ = ["episodes_with_skill"]
