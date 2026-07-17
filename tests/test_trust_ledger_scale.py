"""Fase-C audit mod.11 — trust_ledger.py: stats() must not scan the world.

Measured 2026-07-17 (1M events, this machine), the full journey:
``stats()`` pre-fix = **2213 ms** — a full-table GROUP BY on an unbounded
append-only table, re-run by the console every 30 s (same self-DoS family as
the SSE flow bug). Plain indexes REFUTED first (2213→1887 ms, −15%: the cost
is the row count). Action/layer totals alone measured **1758 ms** — the
residual was the 14-day ``daily`` window still aggregating the window's raw
rows (the second wrong hypothesis, caught by re-measuring). Final design:
per-action, per-layer AND per-day totals, all maintained in the SAME
transaction as the insert; one-time lazy backfill (31 days of day-totals) for
pre-existing stores. Post-fix regime measured: **4 ms** on the same 1M-event
store (550×) — O(1) totals + O(days) series, never O(events).

These pin the CORRECTNESS of the aggregation (totals == raw truth) — the
timing numbers live in the commit/ledger, not in a flaky perf assert.
"""
from __future__ import annotations

import sqlite3
import time

from engram.trust_ledger import TrustLedger


def test_totals_match_raw_after_mixed_writes(tmp_path):
    led = TrustLedger(tmp_path / "l.db")
    led.record("admitted", topic="t")
    led.record("admitted", layers=["L1"], topic="t")
    led.record_many("quarantined", 3, layers=["L1", "L4"])
    led.record("rejected")
    led.record("abstained")
    s = led.stats()
    assert s["ledger"] == {"admitted": 2, "quarantined": 3,
                           "rejected": 1, "abstained": 1}
    # layer attribution: 1 admitted L1 + 3 quarantined L1,L4
    assert s["by_layer"] == {"L1": 4, "L4": 3}


def test_backfill_from_preexisting_rows(tmp_path):
    # a store written by the PREVIOUS ledger version: raw rows, no totals
    db = tmp_path / "old.db"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE trust_ledger (id INTEGER PRIMARY KEY, ts REAL "
                "NOT NULL, action TEXT NOT NULL, layers TEXT NOT NULL "
                "DEFAULT '', topic TEXT NOT NULL DEFAULT '')")
    now = time.time()
    con.executemany(
        "INSERT INTO trust_ledger (ts, action, layers, topic) VALUES (?,?,?,?)",
        [(now, "admitted", "", "t")] * 5
        + [(now, "quarantined", "L1", "t")] * 2)
    con.commit(); con.close()
    led = TrustLedger(db)
    s = led.stats()                        # first read triggers the backfill
    assert s["ledger"]["admitted"] == 5
    assert s["ledger"]["quarantined"] == 2
    assert s["by_layer"] == {"L1": 2}
    # and NEW events keep accumulating on top of the backfilled totals
    led.record("admitted")
    assert led.stats()["ledger"]["admitted"] == 6


def test_daily_window_and_since_survive(tmp_path):
    led = TrustLedger(tmp_path / "d.db")
    led.record("admitted")
    s = led.stats()
    assert s["since"] is not None
    assert len(s["daily"]) == 1
    day = s["daily"][0]
    assert day["admitted"] == 1 and day["quarantined"] == 0


def test_stats_is_o1_reads_not_full_scan(tmp_path):
    # structural pin (not a timing assert): after the fix, per-action totals
    # come from the totals table — verified by poisoning the raw table and
    # checking stats() does NOT re-derive from it.
    led = TrustLedger(tmp_path / "s.db")
    led.record_many("admitted", 4)
    con = sqlite3.connect(led.db_path)
    con.execute("DELETE FROM trust_ledger")   # raw rows gone, totals stay
    con.commit(); con.close()
    assert led.stats()["ledger"]["admitted"] == 4


def test_failopen_still_counts_failures(tmp_path):
    led = TrustLedger(tmp_path / "no" / "such" / "dir" / "x.db")
    led.record("admitted")                    # unwritable → swallowed
    assert led.write_failures == 1
