"""Cycle 194 (2026-05-23) — snapshot_at_time: corpus state as of timestamp T.

Closes gap §5 of docs/sota/temporal-evolution-narrative.md (cycle 192).
Pure function that filters facts by ``(created_at <= T)`` AND
``(superseded_at IS NULL OR superseded_at > T)`` — i.e. facts that
were ALIVE at time T.

Use cases
---------
* Replaying an agent's reasoning trajectory as of a point in time.
* Debugging "how did we conclude X on day Y when we now know Y was
  wrong?".
* Audit / compliance: reconstruct the corpus snapshot for an SLA
  window.

Defensive: missing DB / SQL error → ``[]``, never raises.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


def snapshot_at_time(
    semantic_db: Path | str,
    *,
    as_of_ts: float,
    topic: str | None = None,
    status_floor: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Return facts that were ALIVE at ``as_of_ts``.

    "Alive" means:
      * ``created_at <= as_of_ts`` (already in the corpus), AND
      * EITHER ``superseded_at IS NULL`` (still alive today) OR
        ``superseded_at > as_of_ts`` (alive then, replaced later).

    Args:
        semantic_db: path to ``semantic.db``.
        as_of_ts: epoch seconds; the time to "look at".
        topic: optional exact-match filter on ``topic`` column.
        status_floor: optional minimum status (e.g. ``"verified"``).
            Currently NOT enforced — placeholder for future cycle
            that adds the status hierarchy.
        limit: hard cap on returned rows.

    Returns:
        ``[{"id", "proposition", "topic", "created_at",
            "superseded_at"}, ...]`` ordered by created_at ASC.
        Empty list on missing DB / SQL error.
    """
    p = Path(semantic_db)
    if not p.exists():
        return []
    try:
        conn = sqlite3.connect(str(p))
        try:
            sql = (
                "SELECT id, proposition, topic, created_at, superseded_at "
                "FROM facts WHERE created_at <= ? "
                "AND (superseded_at IS NULL OR superseded_at > ?) "
            )
            params: list[Any] = [float(as_of_ts), float(as_of_ts)]
            if topic is not None:
                sql += "AND topic = ? "
                params.append(str(topic))
            sql += "ORDER BY created_at ASC LIMIT ?"
            params.append(int(limit))
            rows = conn.execute(sql, params).fetchall()
        finally:
            conn.close()
    except sqlite3.Error:
        return []
    out: list[dict[str, Any]] = []
    for fid, prop, top, ts, sup_ts in rows:
        out.append({
            "id": str(fid),
            "proposition": str(prop or ""),
            "topic": str(top or ""),
            "created_at": float(ts or 0.0),
            "superseded_at": float(sup_ts) if sup_ts is not None else None,
        })
    return out


__all__ = ["snapshot_at_time"]
