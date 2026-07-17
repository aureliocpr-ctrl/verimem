"""Last N skills by created_at.

FORGIA pezzo #273 — Wave 72.
"""
from __future__ import annotations

from typing import Any

from .skill import Skill


def skills_recent(
    skills: list[Skill],
    *,
    top_k: int = 20,
    status: str | None = None,
) -> dict[str, Any]:
    """Return last N skills, newest-first. Optional status filter."""
    pool = (
        list(skills)
        if status is None
        else [s for s in skills if s.status == status]
    )
    pool.sort(key=lambda s: -float(getattr(s, "created_at", 0.0) or 0.0))
    records = [
        {
            "id": s.id, "name": s.name,
            "status": s.status, "stage": s.stage,
            "created_at": float(s.created_at),
        }
        for s in pool[:top_k]
    ]
    return {"n_total": len(pool), "skills": records}


__all__ = ["skills_recent"]
