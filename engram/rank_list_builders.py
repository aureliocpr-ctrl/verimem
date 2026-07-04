"""Cycle 196 (2026-05-23) — per-signal rank-list builders for RRF fusion.

Closes gap §5 of docs/sota/multi-signal-fusion.md (cycle 190). Pure
functions that return ranked lists of fact ids for each of HippoAgent's
ranking signals. Feed these into ``engram.multi_signal_fusion.rrf_fuse``
(cycle 191) to produce a fused ranking.

Signals
-------
* ``recency_rank``      — ORDER BY created_at DESC (newest first)
* ``confidence_rank``   — ORDER BY confidence DESC
* ``recency_decayed_rank`` — recency with decay multiplier (cycle 195)

The cosine/keyword/pagerank/community/highway signal builders are
NOT in this module — they already exist as standalone primitives
elsewhere (``semantic.recall``, ``semantic.recall_hybrid``,
``hippo_pagerank``, ``community_detector``, ``highway_nodes``) and
the caller wraps them directly. This module ships ONLY the cheap
SQL-only signals that didn't have a dedicated entry point.

Defensive: missing DB / SQL error → ``[]``, never raises.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Literal

from engram.time_decay_score import decay_score


def recency_rank(
    semantic_db: Path | str,
    *,
    limit: int = 100,
    topic: str | None = None,
) -> list[str]:
    """Return fact ids ordered by ``created_at`` DESC (newest first).

    Defensive: missing DB / SQL error → [].
    """
    p = Path(semantic_db)
    if not p.exists():
        return []
    try:
        conn = sqlite3.connect(str(p))
        try:
            sql = (
                "SELECT id FROM facts "
                "WHERE superseded_by IS NULL "
                "  AND (status IS NULL OR status NOT IN "
                "       ('orphaned', 'quarantined')) "
            )
            params: list[object] = []
            if topic is not None:
                sql += "AND topic = ? "
                params.append(str(topic))
            sql += "ORDER BY created_at DESC LIMIT ?"
            params.append(int(limit))
            rows = conn.execute(sql, params).fetchall()
        finally:
            conn.close()
    except sqlite3.Error:
        return []
    return [str(r[0]) for r in rows]


def confidence_rank(
    semantic_db: Path | str,
    *,
    limit: int = 100,
    topic: str | None = None,
) -> list[str]:
    """Return fact ids ordered by ``confidence`` DESC (most confident first).

    Defensive: missing DB / SQL error → [].
    """
    p = Path(semantic_db)
    if not p.exists():
        return []
    try:
        conn = sqlite3.connect(str(p))
        try:
            sql = (
                "SELECT id FROM facts "
                "WHERE superseded_by IS NULL "
                "  AND (status IS NULL OR status NOT IN "
                "       ('orphaned', 'quarantined')) "
            )
            params: list[object] = []
            if topic is not None:
                sql += "AND topic = ? "
                params.append(str(topic))
            sql += "ORDER BY confidence DESC, created_at DESC LIMIT ?"
            params.append(int(limit))
            rows = conn.execute(sql, params).fetchall()
        finally:
            conn.close()
    except sqlite3.Error:
        return []
    return [str(r[0]) for r in rows]


def recency_decayed_rank(
    semantic_db: Path | str,
    *,
    now: float,
    limit: int = 100,
    topic: str | None = None,
    decay_curve: Literal["exp", "power", "linear"] = "exp",
    half_life_days: float = 14.0,
) -> list[str]:
    """Return fact ids ranked by ``recency × decay_score(age)``.

    Sorts facts by decay-multiplied recency score, descending.
    Defensive: missing DB / SQL error → [].
    """
    p = Path(semantic_db)
    if not p.exists():
        return []
    try:
        conn = sqlite3.connect(str(p))
        try:
            sql = (
                "SELECT id, created_at FROM facts "
                "WHERE superseded_by IS NULL "
                "  AND (status IS NULL OR status NOT IN "
                "       ('orphaned', 'quarantined')) "
            )
            params: list[object] = []
            if topic is not None:
                sql += "AND topic = ? "
                params.append(str(topic))
            sql += "ORDER BY created_at DESC LIMIT ?"
            params.append(int(limit) * 2)  # over-fetch
            rows = conn.execute(sql, params).fetchall()
        finally:
            conn.close()
    except sqlite3.Error:
        return []
    # Score each fact by its decay multiplier and sort.
    scored: list[tuple[str, float]] = []
    for fid, ts in rows:
        age_days = (float(now) - float(ts or 0.0)) / 86400.0
        score = decay_score(
            age_days,
            curve=decay_curve,
            half_life_days=float(half_life_days),
        )
        scored.append((str(fid), float(score)))
    scored.sort(key=lambda kv: -kv[1])
    return [fid for fid, _ in scored[: int(limit)]]


__all__ = [
    "recency_rank",
    "confidence_rank",
    "recency_decayed_rank",
]
