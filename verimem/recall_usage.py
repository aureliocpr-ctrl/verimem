"""Cycle #120 (2026-05-17) — Recall usage observability.

Aurelio direttiva: "memoria AI-driven pilotata da te, sperimenta".

Cycle 117 (TrustSignal) gave the AI visibility on recall quality.
Cycle 120 closes the meta-cognition loop: after retrieving facts, the
AI **declares which it used and which it ignored, with a reason**.

Each declaration is one row in ``recall_usage`` (schema v5). Aggregated
over time, this yields a per-fact ``usage_ratio = n_used / n_recalled``:
a fact recalled 12 times but used only 2 has a 0.17 ratio — a stronger
empirical signal of obsolescence than age alone.

V1 surface (this module):
* ``RecallUsageStore(db_path)`` — SQLite store, schema idempotent.
* ``record(query, hit_fact_id, used, reason)``  → 1 row.
* ``record_batch(query, decisions)`` → many rows in one transaction.
* ``usage_stats(fact_id)`` → ``{n_recalled, n_used, ratio}``.
* ``low_usage_facts(min_recalls, max_ratio)`` → list of candidate fact_ids.

NOT in V1: auto-degrade confidence on low-usage facts. That decision
belongs to a separate decay cycle (would compose with cycle #110.C
existing decay job).
"""
from __future__ import annotations

import sqlite3
import time
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_SCHEMA = """
CREATE TABLE IF NOT EXISTS recall_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,
    query TEXT NOT NULL,
    hit_fact_id TEXT NOT NULL,
    used INTEGER NOT NULL,  -- 0/1
    reason TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_recall_usage_fact
    ON recall_usage(hit_fact_id);
CREATE INDEX IF NOT EXISTS idx_recall_usage_ts
    ON recall_usage(ts);
"""


@dataclass(frozen=True)
class RecallUsageRow:
    id: int
    ts: float
    query: str
    hit_fact_id: str
    used: bool
    reason: str


class RecallUsageStore:
    """SQLite-backed store for recall usage declarations."""

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA busy_timeout=60000;")
        except sqlite3.OperationalError:
            pass
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def record(
        self, *, query: str, hit_fact_id: str, used: bool, reason: str = "",
    ) -> int:
        """Insert one usage declaration. Returns the row id."""
        ts = time.time()
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO recall_usage "
                "(ts, query, hit_fact_id, used, reason) "
                "VALUES (?, ?, ?, ?, ?)",
                (ts, query, hit_fact_id, 1 if used else 0, reason),
            )
            return int(cur.lastrowid or 0)

    def record_batch(
        self, *, query: str,
        decisions: Iterable[tuple[str, bool, str]],
    ) -> int:
        """Insert many declarations for a single query. Returns count."""
        ts = time.time()
        rows = [
            (ts, query, fid, 1 if used else 0, reason)
            for fid, used, reason in decisions
        ]
        if not rows:
            return 0
        with self._connect() as conn:
            conn.executemany(
                "INSERT INTO recall_usage "
                "(ts, query, hit_fact_id, used, reason) "
                "VALUES (?, ?, ?, ?, ?)",
                rows,
            )
            return len(rows)

    def all_for_fact(self, fact_id: str) -> list[RecallUsageRow]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, ts, query, hit_fact_id, used, reason "
                "FROM recall_usage WHERE hit_fact_id = ? "
                "ORDER BY ts DESC",
                (fact_id,),
            ).fetchall()
        return [
            RecallUsageRow(
                id=int(r["id"]),
                ts=float(r["ts"]),
                query=str(r["query"]),
                hit_fact_id=str(r["hit_fact_id"]),
                used=bool(r["used"]),
                reason=str(r["reason"] or ""),
            )
            for r in rows
        ]

    def usage_stats(self, fact_id: str) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS n_recalled, "
                "       COALESCE(SUM(used), 0) AS n_used "
                "FROM recall_usage WHERE hit_fact_id = ?",
                (fact_id,),
            ).fetchone()
        n_recalled = int(row["n_recalled"]) if row else 0
        n_used = int(row["n_used"]) if row else 0
        ratio = (n_used / n_recalled) if n_recalled > 0 else 0.0
        return {
            "fact_id": fact_id,
            "n_recalled": n_recalled,
            "n_used": n_used,
            "ratio": ratio,
        }

    def low_usage_facts(
        self, *, min_recalls: int = 5, max_ratio: float = 0.2,
    ) -> list[dict[str, Any]]:
        """Return fact_ids with at least ``min_recalls`` records AND
        ``usage_ratio <= max_ratio``. Sorted by ratio ascending then
        n_recalled descending (lowest signal first)."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT hit_fact_id, "
                "       COUNT(*) AS n_recalled, "
                "       COALESCE(SUM(used), 0) AS n_used "
                "FROM recall_usage "
                "GROUP BY hit_fact_id "
                "HAVING COUNT(*) >= ?",
                (int(min_recalls),),
            ).fetchall()
        out: list[dict[str, Any]] = []
        for r in rows:
            n_recalled = int(r["n_recalled"])
            n_used = int(r["n_used"])
            ratio = n_used / n_recalled
            if ratio <= max_ratio:
                out.append({
                    "fact_id": str(r["hit_fact_id"]),
                    "n_recalled": n_recalled,
                    "n_used": n_used,
                    "ratio": ratio,
                })
        out.sort(key=lambda x: (x["ratio"], -x["n_recalled"]))
        return out


__all__ = ["RecallUsageStore", "RecallUsageRow"]
