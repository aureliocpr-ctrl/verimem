"""R50: Compute skill chain complexity (self + all ancestors)."""
from __future__ import annotations

from typing import Any


def compute_complexity(
    skill_id: str,
    skills: list[Any],
) -> dict[str, Any]:
    """Total skills in execution chain (BFS, cycle-safe)."""
    by_id = {getattr(s, "id", ""): s for s in skills}
    if skill_id not in by_id:
        return {"complexity": 0, "ancestor_ids": []}

    visited: set[str] = set()
    stack = [skill_id]
    while stack:
        sid = stack.pop()
        if sid in visited:
            continue
        visited.add(sid)
        sk = by_id.get(sid)
        if sk is None:
            continue
        for p in getattr(sk, "parent_skills", []) or []:
            if p not in visited:
                stack.append(p)

    return {
        "complexity": len(visited),
        "ancestor_ids": sorted(visited - {skill_id}),
    }


__all__ = ["compute_complexity"]
