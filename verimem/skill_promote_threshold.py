"""Auto-promote candidate skills by explicit threshold.

FORGIA pezzo #270 — Wave 69. Different from apply_recommendations
(uses full skill_health policy): this is direct threshold control
on min_trials + min_fitness.
"""
from __future__ import annotations

from typing import Any


def promote_by_threshold(
    *,
    agent: Any,
    min_trials: int = 5,
    min_fitness: float = 0.6,
    apply: bool = False,
) -> dict[str, Any]:
    """Promote candidate skills meeting both thresholds."""
    skills_store = getattr(agent, "skills", None)
    if skills_store is None:
        return {
            "proposed": [], "n_proposed": 0, "n_applied": 0,
            "applied": apply,
        }

    proposed: list[dict[str, Any]] = []
    n_applied = 0
    for sk in list(skills_store.all()):
        if sk.status != "candidate":
            continue
        if int(sk.trials) < min_trials:
            continue
        if float(sk.fitness_mean) < min_fitness:
            continue
        proposed.append({
            "skill_id": sk.id,
            "name": sk.name,
            "trials": int(sk.trials),
            "fitness_mean": float(sk.fitness_mean),
        })
        if apply:
            sk.status = "promoted"
            try:
                skills_store.store(sk)
                n_applied += 1
            except Exception:
                pass

    return {
        "proposed": proposed,
        "n_proposed": len(proposed),
        "n_applied": n_applied,
        "applied": apply,
        "min_trials": min_trials,
        "min_fitness": min_fitness,
    }


__all__ = ["promote_by_threshold"]
