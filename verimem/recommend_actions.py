"""Batch curation dashboard: skill_health for ALL skills, grouped
by suggested_action and ranked within each group.

FORGIA pezzo #220 — Wave 19. Answers "which skills need attention?"
in one call.

Group ordering (within group):
  - promote: by fitness_mean DESC (graduate the strongest first)
  - retire: by fitness_mean ASC (cut the worst first)
  - pin: by fitness_mean DESC (lock in the top performer)
  - test: by fitness_variance DESC (sample where uncertainty is high)
  - ok: by fitness_mean DESC (healthy ones, bonus info)
"""
from __future__ import annotations

from typing import Any

from .skill import Skill
from .skill_health import skill_health

_GROUP_SORT = {
    "promote": (lambda s: s["fitness_mean"], True),
    "retire": (lambda s: s["fitness_mean"], False),
    "pin":     (lambda s: s["fitness_mean"], True),
    "test":    (lambda s: s["fitness"]["variance"], True),
    "ok":      (lambda s: s["fitness_mean"], True),
}


def recommend_actions(
    skills: list[Skill],
    *,
    episodes: list[Any] | None = None,
    days_window: float = 7.0,
    top_k_per_group: int = 50,
) -> dict[str, Any]:
    """Compute skill_health for each skill, then bucket by
    suggested_action. Returns a dashboard payload.

    Args:
      - `skills`: full skill pool.
      - `episodes`: optional, propagated to skill_health for
        recency calculations.
      - `days_window`: propagated to skill_health.
      - `top_k_per_group`: cap on each group's size.

    Returns: `{summary, n_total, actions: {promote, retire, test,
    pin, ok}}` with each group a list of compact skill records.
    """
    groups: dict[str, list[dict[str, Any]]] = {
        "promote": [], "retire": [], "test": [], "pin": [], "ok": [],
    }
    for s in skills:
        h = skill_health(s, episodes=episodes, days_window=days_window)
        action = h.get("suggested_action", "ok")
        record = {
            "id": h["id"],
            "name": h["name"],
            "status": h["status"],
            "trials": h["trials"],
            "successes": h["successes"],
            "fitness_mean": h["fitness"]["mean"],
            "fitness_lower_bound": h["fitness"]["lower_bound"],
            "fitness_variance": h["fitness"]["variance"],
            "fitness": h["fitness"],
            "reasoning": h["reasoning"],
        }
        if action not in groups:
            groups[action] = []
        groups[action].append(record)

    # Sort each group.
    for action_name, items in groups.items():
        sort_cfg = _GROUP_SORT.get(action_name)
        if sort_cfg is None:
            keyfn = lambda x: x["fitness_mean"]  # noqa: E731
            reverse = True
        else:
            keyfn, reverse = sort_cfg
        items.sort(key=keyfn, reverse=reverse)
        groups[action_name] = items[:top_k_per_group]

    summary_parts = [
        f"Library curation dashboard ({len(skills)} skills total)."
    ]
    for action_name in ("promote", "retire", "test", "pin", "ok"):
        n = len(groups.get(action_name, []))
        if n > 0:
            summary_parts.append(f"{action_name}: {n}")
    summary = "; ".join(summary_parts) + "."

    return {
        "summary": summary,
        "n_total": len(skills),
        "actions": groups,
    }


__all__ = ["recommend_actions"]
