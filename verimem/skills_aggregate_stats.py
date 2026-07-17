"""Per-stage and per-status skill stats.

FORGIA pezzo #275 — Wave 74.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from .skill import Skill


def aggregate_stats(skills: list[Skill]) -> dict[str, Any]:
    """Stats grouped by stage AND status."""
    by_stage: defaultdict[str, dict[str, Any]] = defaultdict(
        lambda: {"count": 0, "sum_fitness": 0.0}
    )
    by_status: Counter[str] = Counter()

    for s in skills:
        stage = getattr(s, "stage", "") or "(none)"
        by_stage[stage]["count"] += 1
        by_stage[stage]["sum_fitness"] += float(
            getattr(s, "fitness_mean", 0.0)
        )
        by_status[getattr(s, "status", "")] += 1

    result_stage: dict[str, Any] = {}
    for stage, data in by_stage.items():
        result_stage[stage] = {
            "count": data["count"],
            "avg_fitness": (
                data["sum_fitness"] / data["count"]
                if data["count"] > 0 else 0.0
            ),
        }

    return {
        "n_total": len(skills),
        "by_stage": result_stage,
        "by_status": dict(by_status),
    }


__all__ = ["aggregate_stats"]
