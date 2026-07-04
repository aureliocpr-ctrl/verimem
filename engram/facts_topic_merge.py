"""Merge facts by topic.

FORGIA pezzo #260 — Wave 59. Consolidate all facts sharing a topic
into a single summary fact. Useful for knowledge consolidation
without losing source episode lineage.
"""
from __future__ import annotations

from typing import Any


def merge_facts_by_topic(
    facts: list[Any],
    *,
    topic: str,
    separator: str = "; ",
) -> dict[str, Any] | None:
    """Combine all `facts` with `f.topic == topic` into one.

    Returns merged record OR None if no facts match the topic.
    Source episodes are unioned; confidence is average; topic is
    preserved.
    """
    matching = [
        f for f in facts
        if getattr(f, "topic", "") == topic
    ]
    if not matching:
        return None

    propositions = [
        (getattr(f, "proposition", "") or "").strip()
        for f in matching
    ]
    propositions = [p for p in propositions if p]
    merged_prop = separator.join(propositions)

    # Confidence: average.
    confs = [
        float(getattr(f, "confidence", 0.0) or 0.0)
        for f in matching
    ]
    avg_conf = sum(confs) / len(confs) if confs else 0.0

    # source_episodes union (preserve order).
    seen: list[str] = []
    for f in matching:
        for eid in (getattr(f, "source_episodes", []) or []):
            if eid not in seen:
                seen.append(eid)

    merged_ids = [getattr(f, "id", "") for f in matching]

    return {
        "topic": topic,
        "proposition": merged_prop,
        "confidence": float(avg_conf),
        "source_episodes": seen,
        "n_merged": len(matching),
        "merged_ids": merged_ids,
    }


__all__ = ["merge_facts_by_topic"]
