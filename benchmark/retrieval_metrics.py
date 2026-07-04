"""Cycle #113.A (2026-05-17) — retrieval quality metrics + Wilson CI.

Pure math, no I/O. Lives under ``benchmark/`` so the rest of the bench
infrastructure can import without touching Engram modules.

Contracts (see tests/test_retrieval_metrics.py):

- ``precision_at_k(retrieved, relevant, k)``: fraction of top-k items
  that are in the relevant set. Denominator is ``min(k, len(retrieved))``
  semantics? NO — denominator is the actual number of items inspected
  (``min(k, len(retrieved))``) so that "k=10 but only 2 retrieved" still
  uses 2 as denominator (precision = relevant_count / inspected_count).
- ``recall_at_k(retrieved, relevant, k)``: fraction of relevant items
  found in top-k. Empty relevant returns 0 (cannot recall what doesn't
  exist).
- ``mrr(retrieved, relevant)``: reciprocal of the rank of the FIRST
  relevant item (1-indexed). Returns 0 if no relevant found.
- ``wilson_ci(successes, trials, confidence)``: Wilson score interval
  for a binomial proportion, used for A/B compare of retrieval
  variants without assuming normal approximation (handles 0/N and N/N
  gracefully).

Reference: Wilson (1927), Newcombe (1998), Brown/Cai/DasGupta (2001).
"""
from __future__ import annotations

import math
from collections.abc import Iterable

# Inverse normal CDF for common confidence levels — avoids the scipy dep.
# Sourced from standard z-tables; values verified against scipy.stats.norm.
_Z_LOOKUP: dict[float, float] = {
    0.80: 1.2815515655446004,
    0.85: 1.4395314709384563,
    0.90: 1.6448536269514722,
    0.95: 1.959963984540054,
    0.99: 2.5758293035489004,
}


def _z_for_confidence(confidence: float) -> float:
    """Return the two-sided z-score for the given confidence level.

    Linear interpolation between the tabulated points covers the
    intermediate values smoothly. The bench rarely needs more than
    0.95 / 0.99 in practice but this keeps the API forgiving.
    """
    if confidence in _Z_LOOKUP:
        return _Z_LOOKUP[confidence]
    keys = sorted(_Z_LOOKUP.keys())
    if confidence < keys[0]:
        return _Z_LOOKUP[keys[0]]
    if confidence > keys[-1]:
        return _Z_LOOKUP[keys[-1]]
    # Linear interp between bracketing tabulated points.
    for i in range(len(keys) - 1):
        lo, hi = keys[i], keys[i + 1]
        if lo <= confidence <= hi:
            frac = (confidence - lo) / (hi - lo)
            return _Z_LOOKUP[lo] + frac * (_Z_LOOKUP[hi] - _Z_LOOKUP[lo])
    # Should not reach here, but defensive:
    return _Z_LOOKUP[0.95]


def precision_at_k(
    retrieved: list[str] | Iterable[str],
    relevant: set[str],
    k: int,
) -> float:
    """Precision@k. Returns ``unique_hits / inspected_count`` where
    ``inspected_count = min(k, len(retrieved))``.

    Standard IR convention: hits are counted UNIQUE — duplicates in
    the retrieved list do not inflate the numerator. The denominator
    is the raw inspected count so a recall path returning duplicates
    pays for the noise (denominator stays, numerator capped at the
    relevant set size).

    Example: ``retrieved=['a','a','b']`` with ``relevant={'a'}`` and
    k=3 → hits=1 (unique 'a'), inspected=3 → precision = 1/3.
    """
    retrieved_list = list(retrieved)
    if k <= 0 or not retrieved_list or not relevant:
        return 0.0
    inspected = retrieved_list[:k]
    if not inspected:
        return 0.0
    hits = len({r for r in inspected if r in relevant})
    return hits / len(inspected)


def recall_at_k(
    retrieved: list[str] | Iterable[str],
    relevant: set[str],
    k: int,
) -> float:
    """Recall@k. Returns ``hits / len(relevant)`` where hits are the
    UNIQUE relevant items found in the first k slots of ``retrieved``.
    """
    retrieved_list = list(retrieved)
    if not relevant or k <= 0 or not retrieved_list:
        return 0.0
    inspected = retrieved_list[:k]
    hits = {r for r in inspected if r in relevant}
    return len(hits) / len(relevant)


def mrr(
    retrieved: list[str] | Iterable[str],
    relevant: set[str],
) -> float:
    """Mean Reciprocal Rank for a SINGLE query.

    Returns ``1 / rank`` where ``rank`` is the 1-indexed position of
    the FIRST relevant item in ``retrieved``. Returns 0 if no relevant
    found or inputs are empty. For aggregating MRR across queries,
    average the per-query values caller-side.
    """
    retrieved_list = list(retrieved)
    if not relevant or not retrieved_list:
        return 0.0
    for i, item in enumerate(retrieved_list, start=1):
        if item in relevant:
            return 1.0 / i
    return 0.0


def wilson_ci(
    successes: int,
    trials: int,
    confidence: float = 0.95,
) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion.

    Returns ``(lo, hi)`` bounds for the true proportion at the
    requested confidence level. More robust than the normal
    approximation for small N or extreme proportions (handles 0/N
    and N/N without producing negative bounds or bounds > 1).

    Raises:
        ValueError: invalid inputs.
    """
    if confidence <= 0.0 or confidence >= 1.0:
        raise ValueError(
            f"confidence must be in (0, 1), got {confidence}"
        )
    if successes < 0 or trials < 0:
        raise ValueError(
            f"successes and trials must be >= 0, got {successes}/{trials}"
        )
    if successes > trials:
        raise ValueError(
            f"successes ({successes}) cannot exceed trials ({trials})"
        )
    if trials == 0:
        return (0.0, 0.0)

    z = _z_for_confidence(confidence)
    p_hat = successes / trials
    z2 = z * z
    denom = 1.0 + z2 / trials
    center = (p_hat + z2 / (2.0 * trials)) / denom
    half = (
        z * math.sqrt(p_hat * (1.0 - p_hat) / trials + z2 / (4.0 * trials * trials))
    ) / denom
    lo = max(0.0, center - half)
    hi = min(1.0, center + half)
    return (lo, hi)


__all__ = [
    "precision_at_k",
    "recall_at_k",
    "mrr",
    "wilson_ci",
]
