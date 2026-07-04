"""R35: Agent specialization score.

For each agent (identified by topic prefix `agent:<id>/<sub-topic>`),
compute Shannon entropy of sub-topic distribution.

Low entropy = highly specialised. High entropy = generalist.

Classification:
  - entropy <0.5 → "specialist"
  - 0.5..1.5 → "balanced"
  - >1.5 → "generalist"
"""
from __future__ import annotations

import math
from collections import Counter, defaultdict
from typing import Any

from .agent_scope import agent_id_from_topic


def _entropy(counts: list[int]) -> float:
    """Shannon entropy in nats."""
    total = sum(counts)
    if total == 0:
        return 0.0
    h = 0.0
    for c in counts:
        if c <= 0:
            continue
        p = c / total
        h -= p * math.log(p)
    return h


def compute_specialization(
    facts: list[Any],
) -> dict[str, Any]:
    """Per-agent specialization score."""
    by_agent_subtopic: dict[str, Counter] = defaultdict(Counter)
    for f in facts:
        topic = getattr(f, "topic", "") or ""
        agent_id = agent_id_from_topic(topic)
        if not agent_id:
            continue
        # sub-topic after `agent:X/` prefix
        sub = topic.split("/", 1)[1] if "/" in topic else ""
        # use top-level sub-topic for grouping
        sub_top = sub.split("/", 1)[0] if "/" in sub else sub
        by_agent_subtopic[agent_id][sub_top] += 1

    per_agent: list[dict[str, Any]] = []
    for aid, counter in by_agent_subtopic.items():
        ent = _entropy(list(counter.values()))
        if ent < 0.5:
            spec = "specialist"
        elif ent < 1.5:
            spec = "balanced"
        else:
            spec = "generalist"
        per_agent.append({
            "agent_id": aid,
            "n_facts": sum(counter.values()),
            "n_unique_subtopics": len(counter),
            "entropy": round(ent, 3),
            "specialization": spec,
            "top_subtopics": [
                {"sub": s, "count": c}
                for s, c in counter.most_common(5)
            ],
        })
    per_agent.sort(key=lambda a: -a["n_facts"])

    return {
        "per_agent": per_agent,
        "n_agents": len(per_agent),
    }


__all__ = ["compute_specialization"]
