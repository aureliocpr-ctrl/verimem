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

_SCHEMA = """
CREATE TABLE IF NOT EXISTS trust_ledger (
    id INTEGER PRIMARY KEY,
    ts REAL NOT NULL,
    action TEXT NOT NULL,
    layers TEXT NOT NULL DEFAULT '',
    topic TEXT NOT NULL DEFAULT ''
)
"""


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
        conn.execute(_SCHEMA)
        return conn

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
            row = (now, action, ",".join(sorted(set(layers or []))),
                   str(topic or ""))
            with self._connect() as conn:
                conn.executemany(
                    "INSERT INTO trust_ledger (ts, action, layers, topic) "
                    "VALUES (?, ?, ?, ?)", [row] * int(n),
                )
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
                for action, n in conn.execute(
                        "SELECT action, COUNT(*) FROM trust_ledger "
                        "GROUP BY action"):
                    if action in counts:
                        counts[action] = int(n)
                for layers, n in conn.execute(
                        "SELECT layers, COUNT(*) FROM trust_ledger "
                        "WHERE layers != '' GROUP BY layers"):
                    for layer in str(layers).split(","):
                        if layer:
                            by_layer[layer] = by_layer.get(layer, 0) + int(n)
                row = conn.execute(
                    "SELECT MIN(ts) FROM trust_ledger").fetchone()
                since = float(row[0]) if row and row[0] is not None else None
                cutoff = time.time() - max(1, int(daily_days)) * 86400.0
                buckets: dict[str, dict[str, Any]] = {}
                for day, action, n in conn.execute(
                        "SELECT date(ts, 'unixepoch') AS day, action, "
                        "COUNT(*) FROM trust_ledger WHERE ts >= ? "
                        "GROUP BY day, action ORDER BY day ASC", (cutoff,)):
                    b = buckets.setdefault(
                        str(day), {"day": str(day),
                                   **{a: 0 for a in _ACTIONS}})
                    if action in _ACTIONS:
                        b[action] = int(n)
                daily = list(buckets.values())
        except Exception:
            pass
        return {"ledger": counts, "by_layer": by_layer, "since": since,
                "daily": daily}
