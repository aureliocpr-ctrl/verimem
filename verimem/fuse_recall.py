"""Cycle 197 (2026-05-23) — fuse_recall orchestrator using RRF.

Closes gap §5 of docs/sota/multi-signal-fusion.md (cycle 190).
Combines multiple ranked id lists into a single fused recall using
``verimem.multi_signal_fusion.rrf_fuse`` (cycle 191) over the
``rank_list_builders`` primitives (cycle 196).

Design
------
Caller supplies which signals to enable. Each enabled signal
produces its own ranked list of fact ids; ``rrf_fuse`` merges them
into a single fused ranking. This is a thin orchestrator — heavy
lifting lives in the underlying primitives.

Composes-over
-------------
* ``verimem.multi_signal_fusion.rrf_fuse``       (cycle 191)
* ``verimem.rank_list_builders.recency_rank``    (cycle 196)
* ``verimem.rank_list_builders.confidence_rank`` (cycle 196)
* ``verimem.rank_list_builders.recency_decayed_rank`` (cycle 196)

The cosine/keyword signals are NOT pulled in here — that requires
loading sentence-transformers (cycle #24 17s warm-up on cold-start).
The caller of ``fuse_recall`` should pre-compute cosine rank list
elsewhere and pass it via ``extra_rank_lists``.

Defensive
---------
* All builders return [] on missing DB → fuse_recall handles
  gracefully (empty inputs to rrf_fuse → empty output).
* ``enabled_signals=frozenset()`` → empty result, no error.
"""
from __future__ import annotations

from pathlib import Path
from typing import Literal

from verimem.multi_signal_fusion import DEFAULT_K, rrf_fuse
from verimem.rank_list_builders import (
    confidence_rank,
    recency_decayed_rank,
    recency_rank,
)

Signal = Literal["recency", "confidence", "recency_decayed"]

_DEFAULT_SIGNALS: frozenset[str] = frozenset({"recency", "confidence"})


def fuse_recall(
    semantic_db: Path | str,
    *,
    enabled_signals: frozenset[str] | set[str] | None = None,
    extra_rank_lists: list[list[str]] | None = None,
    limit: int = 20,
    per_signal_limit: int = 100,
    topic: str | None = None,
    now: float | None = None,
    half_life_days: float = 14.0,
    k: float = DEFAULT_K,
) -> list[str]:
    """Fuse multiple ranking signals via RRF and return top-``limit``.

    Args:
        semantic_db: path to ``semantic.db``.
        enabled_signals: which builders to call. Default
            ``{"recency", "confidence"}``. Pass empty set to use ONLY
            ``extra_rank_lists`` (e.g. cosine pre-computed elsewhere).
        extra_rank_lists: additional pre-built rank lists. Useful for
            cosine / keyword / pagerank signals computed externally.
            Each entry is an ordered list of fact ids (best first).
        limit: cap on fused output length.
        per_signal_limit: cap per-builder before fusion (cost-control).
        topic: optional topic filter forwarded to builders.
        now: epoch seconds for the decayed-recency builder. Defaults
            to ``time.time()`` if omitted.
        half_life_days: decay half-life for recency_decayed.
        k: RRF smoothing constant.

    Returns:
        List of fact ids in fused-ranking order, length ≤ ``limit``.
        Empty list when all enabled builders return empty AND no
        extra_rank_lists is provided.
    """
    if enabled_signals is None:
        enabled_signals = _DEFAULT_SIGNALS
    elif not isinstance(enabled_signals, (frozenset, set)):
        enabled_signals = frozenset(enabled_signals)

    if now is None:
        import time as _t
        now = _t.time()

    rank_lists: list[list[str]] = []

    if "recency" in enabled_signals:
        rank_lists.append(
            recency_rank(
                semantic_db, limit=per_signal_limit, topic=topic,
            )
        )
    if "confidence" in enabled_signals:
        rank_lists.append(
            confidence_rank(
                semantic_db, limit=per_signal_limit, topic=topic,
            )
        )
    if "recency_decayed" in enabled_signals:
        rank_lists.append(
            recency_decayed_rank(
                semantic_db,
                now=float(now),
                limit=per_signal_limit,
                topic=topic,
                half_life_days=float(half_life_days),
            )
        )

    if extra_rank_lists:
        for lst in extra_rank_lists:
            if lst:
                rank_lists.append(list(lst))

    fused = rrf_fuse(rank_lists, k=float(k))
    return [fid for fid, _ in fused[: int(limit)]]


__all__ = ["fuse_recall", "Signal"]
