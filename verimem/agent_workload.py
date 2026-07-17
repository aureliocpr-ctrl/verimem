"""R28: Agent workload distribution.

Aggregate facts + episodes by agent_id (using R4 namespace
convention). Returns load per agent + imbalance score
(0 = perfect balance, 1 = single agent does everything).
"""
from __future__ import annotations

import math
from collections import defaultdict
from typing import Any

from .agent_scope import agent_id_from_topic


def compute_workload(
    *,
    facts: list[Any],
    episodes: list[Any],
) -> dict[str, Any]:
    """Workload metrics per agent_id."""
    facts_per: dict[str, int] = defaultdict(int)
    for f in facts:
        owner = agent_id_from_topic(getattr(f, "topic", ""))
        if owner:
            facts_per[owner] += 1

    # Episodes don't have explicit agent_id, skip detailed attribution
    # (a future round could mine this from task_text)

    agents = sorted(set(facts_per.keys()))
    per_agent: list[dict[str, Any]] = []
    for aid in agents:
        per_agent.append({
            "agent_id": aid,
            "n_facts": facts_per[aid],
            "n_episodes": 0,  # placeholder for future attribution
        })
    per_agent.sort(key=lambda a: -a["n_facts"])

    # Imbalance: normalized stddev of facts counts
    counts = [a["n_facts"] for a in per_agent]
    imbalance = 0.0
    if counts and max(counts) > 0:
        mean = sum(counts) / len(counts)
        var = sum((c - mean) ** 2 for c in counts) / len(counts)
        stddev = math.sqrt(var)
        # Normalize: stddev / max_count
        imbalance = round(stddev / max(counts), 4)

    return {
        "per_agent": per_agent,
        "imbalance": imbalance,
        "n_agents": len(agents),
        "n_facts_total": sum(facts_per.values()),
        "n_episodes_total": len(episodes),
    }


__all__ = ["compute_workload"]
