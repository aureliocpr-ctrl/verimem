"""Find skills with trials==0.

FORGIA pezzo #265 — Wave 64. Surfaces untested skills as candidates
for practice/testing.
"""
from __future__ import annotations

from typing import Any

from .skill import Skill


def find_untested_skills(
    skills: list[Skill],
    *,
    status: str | None = None,
    top_k: int = 100,
) -> dict[str, Any]:
    """Return skills with trials == 0."""
    filtered = [
        s for s in skills
        if int(getattr(s, "trials", 0) or 0) == 0
        and (status is None or s.status == status)
    ]
    records = [
        {
            "id": s.id, "name": s.name,
            "status": s.status, "stage": s.stage,
        }
        for s in filtered[:top_k]
    ]
    return {"n_total": len(filtered), "skills": records}


__all__ = ["find_untested_skills"]
