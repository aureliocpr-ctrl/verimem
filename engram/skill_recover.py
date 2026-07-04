"""Restore retired skill to candidate.

FORGIA pezzo #257 — Wave 56. Un-retire a skill: status retired ->
candidate. Use case: skill was wrongly culled or upstream heuristic
changed.
"""
from __future__ import annotations

from typing import Any


def recover_skill(
    *,
    skill_id: str,
    agent: Any,
    apply: bool = False,
) -> dict[str, Any]:
    """Move retired skill back to candidate.

    Returns: `{skill_id, found, recovered, applied, before_status}`.
    `recovered=True` only if skill was retired (else no-op).
    """
    skills_store = getattr(agent, "skills", None)
    if skills_store is None:
        return {
            "skill_id": skill_id, "found": False,
            "recovered": False, "applied": False,
            "before_status": "",
        }
    sk = skills_store.get(skill_id)
    if sk is None:
        return {
            "skill_id": skill_id, "found": False,
            "recovered": False, "applied": False,
            "before_status": "",
        }
    before = sk.status
    if before != "retired":
        return {
            "skill_id": skill_id, "found": True,
            "recovered": False, "applied": False,
            "before_status": before,
            "reason": "skill is not retired",
        }
    applied = False
    if apply:
        sk.status = "candidate"
        try:
            skills_store.store(sk)
            applied = True
        except Exception:
            applied = False
    return {
        "skill_id": skill_id,
        "found": True,
        "recovered": True,
        "applied": applied,
        "before_status": before,
    }


__all__ = ["recover_skill"]
