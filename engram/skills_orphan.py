"""Orphan skills (isolated from the lineage DAG).

FORGIA pezzo #278 — Wave 77. A skill is orphan when it has no
parents in the library AND no children. Useful for pruning.
"""
from __future__ import annotations

from typing import Any

from .skill import Skill


def find_orphan_skills(
    skills: list[Skill],
    *,
    top_k: int = 100,
) -> dict[str, Any]:
    """Find skills with no in-library parents AND no children."""
    ids = {s.id for s in skills}
    # Build reverse: parent -> children set.
    has_children: set[str] = set()
    for s in skills:
        for p in (s.parent_skills or []):
            if p in ids:
                has_children.add(p)

    orphans: list[dict[str, Any]] = []
    for s in skills:
        # has at least one parent in library?
        valid_parents = [p for p in (s.parent_skills or []) if p in ids]
        if valid_parents:
            continue
        # has any child?
        if s.id in has_children:
            continue
        orphans.append({
            "id": s.id, "name": s.name,
            "status": s.status, "stage": s.stage,
        })

    return {"n_total": len(orphans), "skills": orphans[:top_k]}


__all__ = ["find_orphan_skills"]
