"""Trust ledger — the persistent counter of what the gate actually DID.

Every memory vendor claims accuracy; none can show the user how many
unsupported claims were quarantined, how many contradicted writes were
rejected, how many times the system said "I don't know" instead of
fabricating. Those events already happen inside Verimem on every call —
they just evaporated when the call returned. This module persists them.

Design constraints (in order):

* **Fail-open.** The ledger is observability, not data-path: a broken
  ledger must never break a write or a read. Every public method swallows
  its own storage errors.
* **No PII.** Events carry action / gate layers / topic — NEVER the
  proposition text. The counter proves behaviour without copying content.
* **Same DB file as the store.** Gateway backups (`gateway backup` walks
  every ``*.db``) and GDPR deletion of a tenant DB cover the ledger for free.

Actions recorded: ``admitted`` (clean write), ``quarantined`` (gate
downgrade), ``rejected`` (gate reject, nothing stored), ``abstained``
(read-path: an explain that honestly returned "no evidence").
"""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Any

_ACTIONS = ("admitted", "quarantined", "rejected", "abstained")

#: mod.11 (2026-07-17): per-action / per-layer TOTALS maintained in the same
#: transaction as the insert, so ``stats()`` reads O(1) rows instead of
#: GROUP-BY-scanning an unbounded events table. Measured on 1M events: 2213 ms
#: per stats() call (the console refreshes every 30 s — the SSE-DoS family);
#: plain indexes were refuted by measurement first (−15%: the cost is the row
#: count), totals bring it to ~3 ms. The raw events table STAYS (audit trail +
#: the 14-day ``daily`` window, served by a ts range-scan index).
_SCHEMA_STMTS = (
    """CREATE TABLE IF NOT EXISTS trust_ledger (
    id INTEGER PRIMARY KEY,
    ts REAL NOT NULL,
    action TEXT NOT NULL,
    layers TEXT NOT NULL DEFAULT '',
    topic TEXT NOT NULL DEFAULT ''
)""",
    "CREATE INDEX IF NOT EXISTS idx_trust_ledger_ts ON trust_ledger(ts)",
    """CREATE TABLE IF NOT EXISTS trust_ledger_totals (
    kind TEXT NOT NULL,
    key TEXT NOT NULL,
    n INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (kind, key)
)""",
)

_BACKFILL_MARK = ("meta", "_backfilled")


class TrustLedger:
    """Append-only event counter living inside the store's SQLite file."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        #: Dropped events in THIS process (review 2026-07-09 #6): fail-open
        #: stays — a broken ledger must never cost a write — but the loss is
        #: now VISIBLE (surfaced by ``Memory.trust_stats`` as
        #: ``ledger_write_failures``) instead of masquerading as zeros.
        self.write_failures: int = 0

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        for stmt in _SCHEMA_STMTS:
            conn.execute(stmt)
        self._ensure_backfill(conn)
        return conn

    def _ensure_backfill(self, conn: sqlite3.Connection) -> None:
        """One-time migration for stores written by the pre-totals ledger:
        derive the totals from the existing raw rows (single full scan), then
        mark done. Concurrent-safe: the mark INSERT is part of the same
        transaction as the derived totals, and INSERT OR IGNORE + the primary
        key make a second racer a no-op."""
        row = conn.execute(
            "SELECT n FROM trust_ledger_totals WHERE kind=? AND key=?",
            _BACKFILL_MARK).fetchone()
        if row is not None:
            return
        for action, n in conn.execute(
                "SELECT action, COUNT(*) FROM trust_ledger GROUP BY action"):
            if action in _ACTIONS:
                conn.execute(
                    "INSERT INTO trust_ledger_totals (kind, key, n) VALUES "
                    "('action', ?, ?) ON CONFLICT(kind, key) DO NOTHING",
                    (action, int(n)))
        # layers are comma-joined per row, so pre-aggregate in Python and write
        # ONE absolute value per layer with DO NOTHING — critic mod.11b
        # (fc026f13): a per-row DO UPDATE accumulate is NOT idempotent, so a
        # concurrent double-derive (TOCTOU on the mark) doubled the per-layer
        # totals. DO NOTHING makes the re-derive a no-op, like action/day.
        layer_counts: dict[str, int] = {}
        for layers, n in conn.execute(
                "SELECT layers, COUNT(*) FROM trust_ledger "
                "WHERE layers != '' GROUP BY layers"):
            for layer in str(layers).split(","):
                if layer:
                    layer_counts[layer] = layer_counts.get(layer, 0) + int(n)
        for layer, n in layer_counts.items():
            conn.execute(
                "INSERT INTO trust_ledger_totals (kind, key, n) VALUES "
                "('layer', ?, ?) ON CONFLICT(kind, key) DO NOTHING",
                (layer, n))
        # day totals: only the recent window matters (the series shows 14
        # days) — backfill 31 days so a wider caller still has data.
        cutoff = time.time() - 31 * 86400.0
        for day, action, n in conn.execute(
                "SELECT date(ts, 'unixepoch') AS d, action, COUNT(*) "
                "FROM trust_ledger WHERE ts >= ? GROUP BY d, action",
                (cutoff,)):
            if action in _ACTIONS:
                conn.execute(
                    "INSERT INTO trust_ledger_totals (kind, key, n) VALUES "
                    "('day', ?, ?) ON CONFLICT(kind, key) DO NOTHING",
                    (f"{day}|{action}", int(n)))
        conn.execute(
            "INSERT OR IGNORE INTO trust_ledger_totals (kind, key, n) "
            "VALUES (?, ?, 1)", _BACKFILL_MARK)

    @staticmethod
    def _bump_totals(conn: sqlite3.Connection, action: str, n: int,
                     layers: list[str], ts: float) -> None:
        conn.execute(
            "INSERT INTO trust_ledger_totals (kind, key, n) VALUES "
            "('action', ?, ?) ON CONFLICT(kind, key) DO UPDATE SET "
            "n = n + excluded.n", (action, n))
        for layer in layers:
            conn.execute(
                "INSERT INTO trust_ledger_totals (kind, key, n) VALUES "
                "('layer', ?, ?) ON CONFLICT(kind, key) DO UPDATE SET "
                "n = n + excluded.n", (layer, n))
        # per-day totals ('day', 'YYYY-MM-DD|action') → the daily series is
        # O(days), not O(events-in-window): the first regime measurement
        # (1758 ms at 1M) showed the window aggregation was the residual cost.
        day = time.strftime("%Y-%m-%d", time.gmtime(ts))
        conn.execute(
            "INSERT INTO trust_ledger_totals (kind, key, n) VALUES "
            "('day', ?, ?) ON CONFLICT(kind, key) DO UPDATE SET "
            "n = n + excluded.n", (f"{day}|{action}", n))

    def record(self, action: str, *, layers: list[str] | None = None,
               topic: str = "") -> None:
        """Append one gate event. Never raises: a ledger failure must not
        cost the caller a write (observability, not data-path)."""
        self.record_many(action, 1, layers=layers, topic=topic)

    def record_many(self, action: str, n: int, *,
                    layers: list[str] | None = None, topic: str = "") -> None:
        """Append ``n`` identical events in one transaction (conversation
        ingest counts whole batches). Same fail-open contract as record()."""
        if action not in _ACTIONS or n <= 0:
            return
        try:
            now = time.time()
            uniq = sorted(set(layers or []))
            row = (now, action, ",".join(uniq), str(topic or ""))
            with self._connect() as conn:
                conn.executemany(
                    "INSERT INTO trust_ledger (ts, action, layers, topic) "
                    "VALUES (?, ?, ?, ?)", [row] * int(n),
                )
                # totals in the SAME transaction: counters can never drift
                # from the raw rows they summarize (mod.11).
                self._bump_totals(conn, action, int(n), uniq, now)
        except Exception:
            self.write_failures += int(n)

    def stats(self, *, daily_days: int = 14) -> dict[str, Any]:
        """Aggregate counters: per-action totals + which gate layer fired +
        the per-day series of the last ``daily_days`` UTC days (``daily``,
        oldest→newest, only days with events — the events already carry
        ``ts``, so the series is a GROUP BY, not a second table).

        Returns zeros (not an error) on a fresh or unreadable store — the
        odometer must be safe to render anywhere.
        """
        counts = {a: 0 for a in _ACTIONS}
        by_layer: dict[str, int] = {}
        since: float | None = None
        daily: list[dict[str, Any]] = []
        try:
            with self._connect() as conn:
                # O(1) rows: the per-action / per-layer totals are maintained
                # transactionally at write time (mod.11) — never a full scan
                # of the unbounded events table (2213 ms at 1M events).
                for kind, key, n in conn.execute(
                        "SELECT kind, key, n FROM trust_ledger_totals"):
                    if kind == "action" and key in counts:
                        counts[key] = int(n)
                    elif kind == "layer" and key:
                        by_layer[key] = int(n)
                row = conn.execute(
                    "SELECT MIN(ts) FROM trust_ledger").fetchone()
                since = float(row[0]) if row and row[0] is not None else None
                cutoff = time.time() - max(1, int(daily_days)) * 86400.0
                cutoff_day = time.strftime("%Y-%m-%d", time.gmtime(cutoff))
                buckets: dict[str, dict[str, Any]] = {}
                # O(days) — day totals are keyed 'YYYY-MM-DD|action', so the
                # lexicographic >= on the key IS the date comparison.
                for key, n in conn.execute(
                        "SELECT key, n FROM trust_ledger_totals WHERE "
                        "kind='day' AND key >= ? ORDER BY key ASC",
                        (cutoff_day,)):
                    day, _, action = str(key).partition("|")
                    b = buckets.setdefault(
                        day, {"day": day, **{a: 0 for a in _ACTIONS}})
                    if action in _ACTIONS:
                        b[action] = int(n)
                daily = list(buckets.values())
        except Exception:
            pass
        return {"ledger": counts, "by_layer": by_layer, "since": since,
                "daily": daily}
