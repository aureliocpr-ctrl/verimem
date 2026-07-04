"""Cluster facts by topic with full members + stats.

FORGIA pezzo #279 — Wave 78 (self-bootstrap demo, Phase E).
Differenza da aggregate_facts_overall: questo restituisce per
ogni topic la lista degli id + un campione di propositions +
avg_confidence. Read-only, pure-local.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any


def facts_cluster_by_topic(
    facts: list[Any],
    *,
    top_k: int = 50,
    max_props_per_cluster: int = 10,
) -> dict[str, Any]:
    """Group facts by topic, return per-topic cluster.

    Args:
      - `facts`: iterable of fact-likes with `id`, `proposition`,
        `topic`, `confidence`.
      - `top_k`: max number of clusters returned (most-populated first).
      - `max_props_per_cluster`: cap on sample propositions per topic.

    Returns: `{n_topics, n_total_facts, clusters}` where each cluster
    has `{topic, count, avg_confidence, fact_ids, sample_propositions}`.
    Sorted by `count` DESC then `topic` ASC for stable output.
    """
    buckets: dict[str, list[Any]] = defaultdict(list)
    for f in facts:
        topic = getattr(f, "topic", "") or "(no topic)"
        buckets[topic].append(f)

    clusters: list[dict[str, Any]] = []
    for topic, group in buckets.items():
        confs = [float(getattr(g, "confidence", 0.0) or 0.0) for g in group]
        avg_conf = sum(confs) / len(confs) if confs else 0.0
        clusters.append({
            "topic": topic,
            "count": len(group),
            "avg_confidence": avg_conf,
            "fact_ids": [getattr(g, "id", "") for g in group],
            "sample_propositions": [
                getattr(g, "proposition", "") for g in group[:max_props_per_cluster]
            ],
        })

    # Sort: count DESC, then topic ASC (stable).
    clusters.sort(key=lambda c: (-c["count"], c["topic"]))

    return {
        "n_total_facts": len(facts),
        "n_topics": len(clusters),
        "clusters": clusters[:top_k],
    }


__all__ = ["facts_cluster_by_topic"]
