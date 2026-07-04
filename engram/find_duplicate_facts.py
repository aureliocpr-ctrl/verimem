"""Batch duplicate-fact detection (semantic memory dedup).

FORGIA pezzo #237 — Wave 36. Same idea as find_duplicate_skills
but for facts: Jaccard on `proposition` tokens. Useful to dedupe
accumulated facts that say the same thing in slightly different
wording.
"""
from __future__ import annotations

import re
from itertools import combinations
from typing import Any

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> set[str]:
    return set(_TOKEN_RE.findall((text or "").lower()))


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    union = len(a | b)
    return len(a & b) / union if union > 0 else 0.0


def find_duplicate_facts(
    facts: list[Any],
    *,
    threshold: float = 0.7,
    top_k: int = 50,
    topic: str | None = None,
) -> dict[str, Any]:
    """Find pairs of facts with token-Jaccard ≥ threshold.

    Args:
      - `facts`: iterable of fact-likes.
      - `threshold`: minimum Jaccard for a pair.
      - `top_k`: cap on returned pairs.
      - `topic`: optional restriction to a single topic.

    Returns: `{n_total_facts, threshold, pairs}` where each pair
    is `{fact_a, fact_b, jaccard, proposition_a, proposition_b}`.
    """
    pool = list(facts)
    if topic is not None:
        pool = [f for f in pool if getattr(f, "topic", "") == topic]

    sigs = [(f, _tokens(getattr(f, "proposition", ""))) for f in pool]
    pairs: list[dict[str, Any]] = []
    for (a, sa), (b, sb) in combinations(sigs, 2):
        j = _jaccard(sa, sb)
        if j >= threshold:
            pairs.append({
                "fact_a": getattr(a, "id", ""),
                "fact_b": getattr(b, "id", ""),
                "proposition_a": (getattr(a, "proposition", "") or "")[:160],
                "proposition_b": (getattr(b, "proposition", "") or "")[:160],
                "jaccard": j,
            })
    pairs.sort(key=lambda p: -p["jaccard"])
    return {
        "n_total_facts": len(pool),
        "threshold": threshold,
        "pairs": pairs[:top_k],
    }


__all__ = ["find_duplicate_facts"]
