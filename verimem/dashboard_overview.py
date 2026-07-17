"""Read-only mega-aggregator dashboard.

FORGIA pezzo #255 — Wave 54. Single-call snapshot of the whole
memory system, suitable for chat-UI dashboard. Differs from
curate_pipeline (action-oriented): purely read-only.

Sections:
  - stats: counts
  - metrics_summary: one-liner string
  - topology: DAG stats
  - size: disk usage (best-effort)
  - recent_facts: latest N facts
  - recent_episodes: latest N episodes
  - top_skills: top by fitness
"""
from __future__ import annotations

from typing import Any

from .briefing import get_briefing
from .metrics_one_liner import metrics_one_liner
from .skills_topology import skills_topology


def dashboard_overview(*, agent: Any) -> dict[str, Any]:
    """Single-call read-only dashboard snapshot."""
    # Reuse briefing for facts/pinned/recent/top_skills/stats.
    brief = get_briefing(agent=agent)

    # Metrics one-liner.
    try:
        m_line = metrics_one_liner(agent=agent)
    except Exception:
        m_line = ""

    # Topology.
    try:
        pool = list(agent.skills.all())
    except Exception:
        pool = []
    topo = skills_topology(pool)

    # Size (optional).
    size: dict[str, Any] = {}
    try:
        from .config import CONFIG
        from .corpus_size import corpus_size_report
        size = corpus_size_report(data_dir=CONFIG.data_dir)
    except Exception:
        size = {"unavailable": True}

    return {
        "stats": brief["stats"],
        "metrics_summary": m_line,
        "topology": topo,
        "size": size,
        "recent_facts": brief["recent_facts"],
        "recent_episodes": brief["recent_episodes"],
        "pinned_episodes": brief["pinned_episodes"],
        "top_skills": brief["top_skills"],
        "summary": brief["summary_text"],
    }


__all__ = ["dashboard_overview"]
