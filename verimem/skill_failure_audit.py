"""Per-skill failure audit.

FORGIA pezzo #231 — Wave 30. For a target skill, returns the
episodes where it was used AND the outcome was failure. Useful
debugging tool: "perché questo skill sta fallendo?".
"""
from __future__ import annotations

from typing import Any


def skill_failure_audit(
    *,
    skill_id: str,
    episodes: list[Any],
    top_k: int = 20,
) -> dict[str, Any]:
    """Return per-skill failure breakdown.

    Args:
      - `skill_id`: target skill.
      - `episodes`: iterable of episode-likes.
      - `top_k`: cap on `failures` list (sorted by recency DESC).

    Returns: `{skill_id, n_total_uses, n_failures, failure_rate,
    failures: [...]}`.
    """
    failures: list[dict[str, Any]] = []
    n_total_uses = 0
    n_failures = 0
    for ep in episodes:
        used = set(getattr(ep, "skills_used", None) or [])
        if skill_id not in used:
            continue
        n_total_uses += 1
        if getattr(ep, "outcome", "") == "failure":
            n_failures += 1
            failures.append({
                "id": getattr(ep, "id", ""),
                "task_text": (getattr(ep, "task_text", "") or "")[:200],
                "created_at": float(getattr(ep, "created_at", 0.0)),
            })

    failures.sort(key=lambda r: -r["created_at"])
    failure_rate = (
        n_failures / n_total_uses if n_total_uses > 0 else None
    )
    return {
        "skill_id": skill_id,
        "n_total_uses": n_total_uses,
        "n_failures": n_failures,
        "failure_rate": failure_rate,
        "failures": failures[:top_k],
    }


__all__ = ["skill_failure_audit"]
