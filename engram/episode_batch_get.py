"""Multi-id episode lookup in one call.

FORGIA pezzo #267 — Wave 66.
"""
from __future__ import annotations

from typing import Any


def episode_batch_get(
    *,
    memory: Any,
    episode_ids: list[str],
) -> dict[str, Any]:
    """Fetch multiple episodes by id. Preserves input order;
    separates missing ids."""
    found: list[dict[str, Any]] = []
    missing: list[str] = []
    for eid in episode_ids:
        ep = memory.get(eid) if hasattr(memory, "get") else None
        if ep is None:
            missing.append(eid)
        else:
            found.append({
                "id": getattr(ep, "id", ""),
                "task_text": (getattr(ep, "task_text", "") or "")[:300],
                "outcome": getattr(ep, "outcome", ""),
                "skills_used": list(
                    getattr(ep, "skills_used", []) or []
                ),
            })
    return {
        "episodes": found,
        "missing": missing,
        "n_found": len(found),
        "n_missing": len(missing),
    }


__all__ = ["episode_batch_get"]
