"""Skill provenance episode lookup.

FORGIA pezzo #271 — Wave 70. Return episodes that spawned the
target skill (via consolidate's NREM/REM stages).
"""
from __future__ import annotations

from typing import Any


def skill_provenance(
    *,
    skill_id: str,
    agent: Any,
) -> dict[str, Any]:
    """Resolve `skill.provenance_episodes` ids to full episode records."""
    skills_store = getattr(agent, "skills", None)
    memory = getattr(agent, "memory", None)
    if skills_store is None or memory is None:
        return {
            "skill_id": skill_id, "found": False,
            "episodes": [], "missing": [], "n_provenance_ids": 0,
        }
    sk = skills_store.get(skill_id)
    if sk is None:
        return {
            "skill_id": skill_id, "found": False,
            "episodes": [], "missing": [], "n_provenance_ids": 0,
        }
    prov_ids = list(getattr(sk, "provenance_episodes", []) or [])
    eps_records: list[dict[str, Any]] = []
    missing: list[str] = []
    for eid in prov_ids:
        ep = memory.get(eid) if hasattr(memory, "get") else None
        if ep is None:
            missing.append(eid)
        else:
            eps_records.append({
                "id": getattr(ep, "id", ""),
                "task_text": (getattr(ep, "task_text", "") or "")[:200],
                "outcome": getattr(ep, "outcome", ""),
            })
    return {
        "skill_id": skill_id,
        "found": True,
        "episodes": eps_records,
        "missing": missing,
        "n_provenance_ids": len(prov_ids),
    }


__all__ = ["skill_provenance"]
