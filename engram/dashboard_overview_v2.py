"""Cycle #88 — unified dashboard v2 (orphan + freshness + health).

DISTINCT from FORGIA #255 ``dashboard_overview`` which is a read-only
chat-UI snapshot. This v2 is the project-aware health overview
built on top of cycle #78-87 tools: corpus_health_metrics +
topic_cleanup_suggestions + per-project facts_freshness_check.
"""
from __future__ import annotations

from typing import Any

from .corpus_health_metrics import corpus_health_metrics
from .freshness_check import facts_freshness_check
from .semantic import SemanticMemory
from .topic_cleanup_suggestions import topic_cleanup_suggestions


def dashboard_overview_v2(
    semantic: SemanticMemory, *,
    project_globs: list[str] | None = None,
    freshness_threshold_days: float = 30.0,
    freshness_sim_threshold: float = 0.85,
    top_topics_k: int = 10,
    max_orphan_suggestions: int = 10,
    orphan_sim_threshold: float = 0.6,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "health": corpus_health_metrics(semantic, top_topics_k=top_topics_k),
        "orphan_suggestions": topic_cleanup_suggestions(
            semantic,
            max_suggestions=max_orphan_suggestions,
            sim_threshold=orphan_sim_threshold,
        ),
        "freshness_by_project": {},
    }
    for glob in project_globs or []:
        try:
            out["freshness_by_project"][glob] = facts_freshness_check(
                semantic, glob,
                threshold_days=freshness_threshold_days,
                sim_threshold=freshness_sim_threshold,
                max_results=10,
            )
        except Exception as exc:  # noqa: BLE001
            out["freshness_by_project"][glob] = {
                "error": str(exc), "topic_glob": glob,
            }
    return out


__all__ = ["dashboard_overview_v2"]
