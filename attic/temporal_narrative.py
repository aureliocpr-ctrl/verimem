"""Cycle 193 (2026-05-23) — temporal narrative reconstruction.

Closes gap §5.1 of docs/sota/temporal-evolution-narrative.md
(cycle 192). Pure function that walks the lineage_to + superseded_by
DAGs around a seed fact and returns an ordered narrative of related
facts with role labels.

Roles
-----
* ``root``        seed fact itself
* ``antecedent``  reachable via ``lineage_to`` (parent chain)
* ``descendant``  reachable via reverse ``lineage_to`` (children)
* ``revision``    same chain via ``superseded_by`` (sideways)
* ``context``     same topic, within ``window_days``, not directly linked

Defensive: missing DB / unknown seed → empty list, never raises.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

_DEFAULT_WINDOW_DAYS: float = 30.0
_SEC_PER_DAY: float = 86400.0


def _now() -> float:
    import time as _t
    return _t.time()


def reconstruct_narrative(
    semantic_db: Path | str,
    *,
    seed_fact_id: str,
    window_days: float = _DEFAULT_WINDOW_DAYS,
    now: float | None = None,
    max_entries: int = 50,
) -> list[dict[str, Any]]:
    """Return an ordered narrative around ``seed_fact_id``.

    Args:
        semantic_db: path to ``semantic.db``.
        seed_fact_id: pivot fact whose narrative we reconstruct.
        window_days: time window (before AND after seed.created_at)
            within which ``context`` (same-topic) facts are gathered.
        now: epoch seconds; defaults to time.time(). Allows
            deterministic testing of ``age_days`` computation.
        max_entries: hard cap on return length.

    Returns:
        ``[{"fact_id", "ts", "age_days", "role", "edge_to_seed"}, ...]``
        sorted by ts ASC (chronological). The seed itself ALWAYS
        appears with role='root'. Empty list on missing DB or
        unknown seed.
    """
    p = Path(semantic_db)
    if not p.exists():
        return []
    now_ts = float(now if now is not None else _now())

    try:
        conn = sqlite3.connect(str(p))
        try:
            seed_row = conn.execute(
                "SELECT id, created_at, topic FROM facts WHERE id = ?",
                (seed_fact_id,),
            ).fetchone()
            if seed_row is None:
                return []
            seed_id, seed_ts, seed_topic = (
                str(seed_row[0]),
                float(seed_row[1] or 0.0),
                str(seed_row[2] or ""),
            )

            narrative: list[dict[str, Any]] = []
            seen: set[str] = set()

            def _add(fact_id: str, ts: float, role: str,
                     edge: str | None) -> None:
                if fact_id in seen:
                    return
                seen.add(fact_id)
                narrative.append({
                    "fact_id": fact_id,
                    "ts": float(ts),
                    "age_days": (now_ts - float(ts)) / _SEC_PER_DAY,
                    "role": role,
                    "edge_to_seed": edge,
                })

            # Root
            _add(seed_id, seed_ts, "root", None)

            # Antecedents: follow lineage_to backward.
            cur_id = seed_id
            for _ in range(20):  # hard cap chain depth
                row = conn.execute(
                    "SELECT lineage_to FROM facts WHERE id = ?",
                    (cur_id,),
                ).fetchone()
                if not row or not row[0]:
                    break
                parent_id = str(row[0])
                if parent_id in seen:
                    break
                p_row = conn.execute(
                    "SELECT created_at FROM facts WHERE id = ?",
                    (parent_id,),
                ).fetchone()
                if p_row is None:
                    break
                _add(parent_id, float(p_row[0] or 0.0),
                     "antecedent", "lineage_to")
                cur_id = parent_id

            # Descendants: facts whose lineage_to == seed_id (one hop).
            desc_rows = conn.execute(
                "SELECT id, created_at FROM facts "
                "WHERE lineage_to = ? AND superseded_by IS NULL "
                "LIMIT 50",
                (seed_id,),
            ).fetchall()
            for d_id, d_ts in desc_rows:
                _add(str(d_id), float(d_ts or 0.0),
                     "descendant", "lineage_from")

            # Revisions: facts that supersede this one, OR are
            # superseded BY this one.
            rev_rows = conn.execute(
                "SELECT id, created_at FROM facts "
                "WHERE superseded_by = ? OR id IN "
                "(SELECT superseded_by FROM facts WHERE id = ?) "
                "LIMIT 20",
                (seed_id, seed_id),
            ).fetchall()
            for r_id, r_ts in rev_rows:
                _add(str(r_id), float(r_ts or 0.0),
                     "revision", "supersedes")

            # Context: same topic, within window_days, not directly
            # linked above. Cheap SQL filter.
            if seed_topic:
                lo = seed_ts - window_days * _SEC_PER_DAY
                hi = seed_ts + window_days * _SEC_PER_DAY
                ctx_rows = conn.execute(
                    "SELECT id, created_at FROM facts "
                    "WHERE topic = ? AND created_at BETWEEN ? AND ? "
                    "  AND superseded_by IS NULL "
                    "ORDER BY created_at ASC LIMIT 100",
                    (seed_topic, lo, hi),
                ).fetchall()
                for c_id, c_ts in ctx_rows:
                    _add(str(c_id), float(c_ts or 0.0),
                         "context", "same_topic")
        finally:
            conn.close()
    except sqlite3.Error:
        return []

    # Sort chronologically, then cap.
    narrative.sort(key=lambda e: (e["ts"], e["fact_id"]))
    return narrative[: int(max_entries)]


__all__ = ["reconstruct_narrative"]
