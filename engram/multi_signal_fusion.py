"""Cycle 191 (2026-05-23) — Reciprocal Rank Fusion (RRF) primitive.

Closes gap §5.1 of docs/sota/multi-signal-fusion.md (cycle 190).
Pure function that combines N independently-ranked id lists into a
single fused ranking using Cormack-Clarke-Buettcher 2009 RRF formula:

    score(d) = Σ_signal  1 / (k + rank_signal(d))

with k=60 (Cormack default, smooths the head of each list).

Why RRF (vs weighted linear / LTR):
  * NO training required.
  * Robust to signal-scale mismatches (cosine vs PageRank vs recency).
  * Easy to A/B-test (toggle signals in/out by adding/removing lists).

This module ships ONLY the fusion primitive. The per-signal rank-list
builders + the high-level ``fuse_recall`` orchestrator are scope of
cycles 192/193.
"""
from __future__ import annotations

from collections.abc import Iterable

#: Cormack 2009 default. Higher k → smoother (less emphasis on top
#: ranks); lower k → sharper (top ranks dominate). 60 is a robust
#: middle ground confirmed by 15+ years of search-engine practice.
DEFAULT_K: float = 60.0


def rrf_fuse(
    rank_lists: Iterable[Iterable[str]],
    *,
    k: float = DEFAULT_K,
) -> list[tuple[str, float]]:
    """Combine N ranked id lists into a single fused ranking.

    Args:
        rank_lists: each entry is an ordered iterable of fact ids
            (rank-1 = first element). Empty inner lists allowed.
        k: RRF smoothing constant. Must be > 0 (use ``DEFAULT_K``
            unless you have a measured reason to override).

    Returns:
        ``[(fact_id, fused_score), ...]`` sorted by score DESC.
        Every fact_id present in ANY input list appears at least
        once with its summed score.
    """
    if k <= 0:
        # Defensive: a non-positive k makes 1/(k+rank) undefined or
        # negative. Coerce to Cormack default.
        k = DEFAULT_K

    scores: dict[str, float] = {}
    first_rank: dict[str, int] = {}   # rank in the FIRST list (the dense/CE primary signal)
    for li, one_list in enumerate(rank_lists):
        for rank_idx, fact_id in enumerate(one_list):
            if not isinstance(fact_id, str):
                # Skip malformed entries; never raise.
                continue
            rank = rank_idx + 1  # rank-1 indexing per Cormack 2009
            contrib = 1.0 / (float(k) + float(rank))
            scores[fact_id] = scores.get(fact_id, 0.0) + contrib
            if li == 0 and fact_id not in first_rank:
                first_rank[fact_id] = rank

    # Sort by score DESC; break ties by rank in the FIRST list (the dense/CE primary
    # signal) so a CE-top fact is NOT displaced by a random fact_id at a score tie (WF3
    # 2026-06-20); id only as the final deterministic fallback.
    _NO_FIRST = 1 << 30
    return sorted(
        scores.items(),
        key=lambda kv: (-kv[1], first_rank.get(kv[0], _NO_FIRST), kv[0]),
    )


__all__ = ["rrf_fuse", "DEFAULT_K"]
