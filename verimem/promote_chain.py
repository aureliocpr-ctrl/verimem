"""Recursive promote a skill + its parent chain.

FORGIA pezzo #245 — Wave 44. When a SCHEMA meta-skill earns
promotion, its constituents (parent_skills) should typically be
promoted too. This walks the parent chain safely (cycle-protected)
and reports + optionally applies promotion.
"""
from __future__ import annotations

from typing import Any


def promote_chain(
    *,
    skill_id: str,
    agent: Any,
    apply: bool = False,
) -> dict[str, Any]:
    """Walk parent_skills recursively and promote.

    Args:
      - `skill_id`: starting skill.
      - `agent`: must expose `.skills.get/store/all`.
      - `apply`: when True, persists status="promoted" via store().

    Returns: `{found, promoted, skipped_already_promoted, applied}`.
    """
    skills_store = getattr(agent, "skills", None)
    if skills_store is None:
        return {
            "found": False, "promoted": [],
            "skipped_already_promoted": [], "applied": apply,
        }

    target = skills_store.get(skill_id)
    if target is None:
        return {
            "found": False, "promoted": [],
            "skipped_already_promoted": [], "applied": apply,
        }

    promoted: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    visited: set[str] = set()
    queue = [skill_id]

    while queue:
        sid = queue.pop(0)
        if sid in visited:
            continue
        visited.add(sid)
        sk = skills_store.get(sid)
        if sk is None:
            continue
        record = {
            "id": sk.id, "name": sk.name,
            "before_status": sk.status,
        }
        if sk.status == "promoted":
            skipped.append(record)
        else:
            if apply:
                sk.status = "promoted"
                try:
                    skills_store.store(sk)
                except Exception:
                    pass
            promoted.append({**record, "after_status": "promoted"})
        # Enqueue parents.
        for parent_id in (sk.parent_skills or []):
            if parent_id not in visited:
                queue.append(parent_id)

    return {
        "found": True,
        "promoted": promoted,
        "skipped_already_promoted": skipped,
        "applied": apply,
    }


__all__ = ["promote_chain"]
