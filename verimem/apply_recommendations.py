"""Apply skill_health recommendations as batch status changes.

FORGIA pezzo #233 — Wave 32. Takes the recommend_actions dashboard
(#220) and ACTUALLY applies the suggested promote/retire in batch.
Dry-run by default; `apply=True` mutates `Skill.status` and calls
`skills.store()` for each affected skill.
"""
from __future__ import annotations

from typing import Any

from .skill_health import skill_health

# Map suggested_action -> the resulting Skill.status.
_ACTION_TO_STATUS = {
    "promote": "promoted",
    "retire": "retired",
    # "test" / "pin" / "ok" don't directly change status.
}


def apply_recommendations(
    *,
    agent: Any,
    actions: list[str] | None = None,
    apply: bool = False,
    days_window: float = 7.0,
) -> dict[str, Any]:
    """Run skill_health for every skill, then optionally apply the
    suggested actions.

    Args:
      - `agent`: HippoAgent (or duck-type with `.skills.all/store`).
      - `actions`: list of action types to apply. Default
        `["promote", "retire"]`. Use a subset to do partial cleanup.
      - `apply`: when True, persists changes via `skills.store()`.
        Default False (dry-run).
      - `days_window`: propagated to skill_health for recency.

    Returns: `{n_proposed, n_applied, actions, changes: [...]}` where
    `changes` is a list of `{skill_id, name, before_status,
    after_status, action, reasoning}`.
    """
    if actions is None:
        actions = ["promote", "retire"]

    episodes = []
    try:
        mem = getattr(agent, "memory", None)
        if mem is not None and hasattr(mem, "all"):
            episodes = mem.all(limit=2000)
    except Exception:
        episodes = []

    skills_store = getattr(agent, "skills", None)
    if skills_store is None:
        return {
            "n_proposed": 0,
            "n_applied": 0,
            "actions": actions,
            "changes": [],
        }

    changes: list[dict[str, Any]] = []
    n_proposed = 0
    n_applied = 0

    for sk in list(skills_store.all()):
        h = skill_health(sk, episodes=episodes, days_window=days_window)
        action = h["suggested_action"]
        if action not in actions:
            continue
        target_status = _ACTION_TO_STATUS.get(action)
        if target_status is None:
            continue
        if sk.status == target_status:
            continue  # already there
        n_proposed += 1
        before = sk.status
        if apply:
            sk.status = target_status
            try:
                skills_store.store(sk)
                n_applied += 1
            except Exception:
                continue
        changes.append({
            "skill_id": sk.id,
            "name": sk.name,
            "before_status": before,
            "after_status": target_status if apply else target_status,
            "action": action,
            "reasoning": h["reasoning"],
            "applied": apply,
        })

    return {
        "n_proposed": n_proposed,
        "n_applied": n_applied,
        "actions": actions,
        "changes": changes,
    }


__all__ = ["apply_recommendations"]
