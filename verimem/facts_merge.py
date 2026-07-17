"""Merge two duplicate facts into one.

FORGIA pezzo #241 — Wave 40. After find_duplicate_facts (#237)
flags a pair, this combines them: pick a primary, union of
source_episodes, configurable confidence combination.

Returns a payload — does NOT directly mutate the semantic store.
Caller can use it to call `hippo_remember` (new) + `hippo_fact_forget`
(both old) atomically.
"""
from __future__ import annotations

from typing import Any

_VALID_STRATEGIES = ("average", "max", "min")


def merge_facts(
    fact_a: Any,
    fact_b: Any,
    *,
    keeper: str = "a",
    confidence_strategy: str = "average",
) -> dict[str, Any]:
    """Combine two facts and return the merged record.

    Args:
      - `fact_a`, `fact_b`: the two duplicates.
      - `keeper`: which one to use as primary ('a' or 'b'). The
        primary's proposition + topic are inherited; secondary
        contributes source_episodes.
      - `confidence_strategy`: 'average' (default), 'max', or 'min'.

    Returns: dict with `primary_id, secondary_id, proposition,
    topic, confidence, source_episodes`.
    """
    if keeper not in ("a", "b"):
        raise ValueError(f"keeper must be 'a' or 'b'; got {keeper!r}")
    if confidence_strategy not in _VALID_STRATEGIES:
        raise ValueError(
            f"confidence_strategy must be one of "
            f"{_VALID_STRATEGIES}; got {confidence_strategy!r}"
        )

    primary = fact_a if keeper == "a" else fact_b
    secondary = fact_b if keeper == "a" else fact_a

    # Topic: prefer non-empty from primary, fall back to secondary.
    primary_topic = getattr(primary, "topic", "") or ""
    if not primary_topic:
        primary_topic = getattr(secondary, "topic", "") or ""

    # source_episodes union.
    ep_a = list(getattr(fact_a, "source_episodes", []) or [])
    ep_b = list(getattr(fact_b, "source_episodes", []) or [])
    combined_eps = list(dict.fromkeys(ep_a + ep_b))  # preserves order

    # Confidence combination.
    ca = float(getattr(fact_a, "confidence", 0.0))
    cb = float(getattr(fact_b, "confidence", 0.0))
    if confidence_strategy == "average":
        confidence = (ca + cb) / 2
    elif confidence_strategy == "max":
        confidence = max(ca, cb)
    else:
        confidence = min(ca, cb)

    return {
        "primary_id": getattr(primary, "id", ""),
        "secondary_id": getattr(secondary, "id", ""),
        "proposition": getattr(primary, "proposition", ""),
        "topic": primary_topic,
        "confidence": float(confidence),
        "source_episodes": combined_eps,
    }


__all__ = ["merge_facts"]
