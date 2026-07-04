"""Facts overall aggregate stats.

FORGIA pezzo #277 — Wave 76.
"""
from __future__ import annotations

from collections import Counter
from typing import Any


def aggregate_facts_overall(
    facts: list[Any],
    *,
    top_k_topics: int = 10,
) -> dict[str, Any]:
    """n_total + topics + avg_conf + conf-distribution buckets."""
    n_total = len(facts)
    if n_total == 0:
        return {
            "n_total": 0, "n_topics": 0,
            "avg_confidence": 0.0,
            "top_topics": [],
            "conf_distribution": {
                "high": 0, "mid": 0, "low": 0,
            },
        }

    topic_counts: Counter[str] = Counter()
    confs: list[float] = []
    high = mid = low = 0
    for f in facts:
        topic = getattr(f, "topic", "") or "(no topic)"
        topic_counts[topic] += 1
        c = float(getattr(f, "confidence", 0.0) or 0.0)
        confs.append(c)
        if c >= 0.8:
            high += 1
        elif c >= 0.5:
            mid += 1
        else:
            low += 1

    avg_conf = sum(confs) / len(confs) if confs else 0.0

    top_topics = [
        {"topic": t, "count": c}
        for t, c in topic_counts.most_common(top_k_topics)
    ]

    return {
        "n_total": n_total,
        "n_topics": len(topic_counts),
        "avg_confidence": avg_conf,
        "top_topics": top_topics,
        "conf_distribution": {"high": high, "mid": mid, "low": low},
    }


__all__ = ["aggregate_facts_overall"]
