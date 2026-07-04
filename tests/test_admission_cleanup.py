"""TDD for the reversible telemetry backlog cleanup (engram.admission_cleanup).

dry_run default = reports only (no mutation). dry_run=False moves telemetry out
of `facts` into `telemetry` (non-lossy essentials), leaves real facts untouched.
Hermetic: tmp DB, never ~/.engram.
"""
from __future__ import annotations

import sqlite3

from engram.admission_cleanup import cleanup_telemetry


def _make_db(path):
    c = sqlite3.connect(path)
    c.execute(
        "CREATE TABLE facts (id TEXT PRIMARY KEY, topic TEXT, proposition TEXT, "
        "status TEXT, writer_role TEXT, source_episodes TEXT, created_at REAL, "
        "superseded_by TEXT)"
    )
    c.executemany(
        "INSERT INTO facts VALUES (?,?,?,?,?,?,?,?)",
        [
            ("t1", "bus/ambient/events", "event fired", "model_claim", "agent_inference", "", 1.0, None),
            ("t2", "metric/cpu", "cpu 80%", "model_claim", "agent_inference", "", 2.0, None),
            ("r1", "decisions/x", "we chose e5-base", "verified", "user", "ep1", 3.0, None),
            ("r2", "lessons/y", "approach worked", "model_claim", "agent_inference", "ep2", 4.0, None),
        ],
    )
    c.commit()
    c.close()


def _count(path, sql):
    c = sqlite3.connect(path)
    try:
        return c.execute(sql).fetchone()[0]
    finally:
        c.close()


def test_dry_run_reports_without_mutating(tmp_path):
    db = tmp_path / "s.db"
    _make_db(db)
    r = cleanup_telemetry(db, dry_run=True)
    assert r["scanned"] == 4
    assert r["telemetry_found"] == 2  # bus/ + metric/
    assert r["moved"] == 0
    assert _count(db, "SELECT COUNT(*) FROM facts") == 4  # untouched


def test_moves_telemetry_out_keeps_real_facts(tmp_path):
    db = tmp_path / "s.db"
    _make_db(db)
    r = cleanup_telemetry(db, dry_run=False)
    assert r["moved"] == 2
    assert _count(db, "SELECT COUNT(*) FROM facts WHERE topic LIKE 'bus/%' OR topic LIKE 'metric/%'") == 0
    assert _count(db, "SELECT COUNT(*) FROM telemetry") == 2
    # real facts (decisions/, lessons/) remain in the curated corpus
    assert _count(db, "SELECT COUNT(*) FROM facts") == 2
    assert _count(db, "SELECT COUNT(*) FROM facts WHERE id IN ('r1','r2')") == 2
    # essentials preserved (non-lossy)
    c = sqlite3.connect(db)
    row = c.execute("SELECT topic, proposition, created_at FROM telemetry WHERE id='t1'").fetchone()
    c.close()
    assert row == ("bus/ambient/events", "event fired", 1.0)


def test_idempotent_second_run_moves_nothing(tmp_path):
    db = tmp_path / "s.db"
    _make_db(db)
    cleanup_telemetry(db, dry_run=False)
    r2 = cleanup_telemetry(db, dry_run=False)
    assert r2["telemetry_found"] == 0 and r2["moved"] == 0
