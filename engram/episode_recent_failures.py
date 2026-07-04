"""Recent failures only.

FORGIA pezzo #276 — Wave 75. Filter + sort newest-first.
"""
from __future__ import annotations

from typing import Any


def recent_failures(
    episodes: list[Any],
    *,
    top_k: int = 20,
) -> dict[str, Any]:
    """Last N failed episodes, newest-first."""
    failures = [
        e for e in episodes
        if getattr(e, "outcome", "") == "failure"
    ]
    failures.sort(
        key=lambda e: -float(getattr(e, "created_at", 0.0) or 0.0),
    )
    records = [
        {
            "id": getattr(e, "id", ""),
            "task_text": (getattr(e, "task_text", "") or "")[:200],
            "created_at": float(getattr(e, "created_at", 0.0) or 0.0),
        }
        for e in failures[:top_k]
    ]
    return {
        "n_total_failures": len(failures),
        "episodes": records,
    }


__all__ = ["recent_failures"]
