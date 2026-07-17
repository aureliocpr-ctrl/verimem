"""Cycle 194 (2026-05-23) — snapshot_at_time tests.

RED marker: ``from verimem.snapshot_at_time import snapshot_at_time``
must fail on master.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

# RED MARKER
from verimem.snapshot_at_time import snapshot_at_time

_SCHEMA = """
CREATE TABLE IF NOT EXISTS facts (
    id TEXT PRIMARY KEY,
    proposition TEXT,
    topic TEXT,
    lineage_to TEXT,
    superseded_by TEXT,
    superseded_at REAL,
    status TEXT DEFAULT 'model_claim',
    created_at REAL
);
"""


@pytest.fixture
def time_db(tmp_path: Path) -> Path:
    """Five facts at different times + supersession events:

      f1 ts=1000  alive forever
      f2 ts=2000  superseded at 2500
      f3 ts=2200  alive forever
      f4 ts=3000  alive forever (different topic)
      f5 ts=2800  superseded at 3500
    """
    db_path = tmp_path / "semantic.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript(_SCHEMA)
    rows = [
        ("f1", "p1", "t/a", None, None, None,    "model_claim", 1000.0),
        ("f2", "p2", "t/a", None, "f3",  2500.0, "model_claim", 2000.0),
        ("f3", "p3", "t/a", None, None, None,    "model_claim", 2200.0),
        ("f4", "p4", "t/b", None, None, None,    "model_claim", 3000.0),
        ("f5", "p5", "t/a", None, None,  3500.0, "model_claim", 2800.0),
    ]
    conn.executemany(
        "INSERT INTO facts (id, proposition, topic, lineage_to, "
        "superseded_by, superseded_at, status, created_at) "
        "VALUES (?,?,?,?,?,?,?,?)",
        rows,
    )
    conn.commit()
    conn.close()
    return db_path


class TestSnapshotAtTime:
    def test_missing_db_returns_empty(self, tmp_path: Path) -> None:
        out = snapshot_at_time(tmp_path / "nope.db", as_of_ts=2000.0)
        assert out == []

    def test_snapshot_at_t1500_returns_f1_only(
        self, time_db: Path,
    ) -> None:
        """At ts=1500 only f1 (created 1000) is alive."""
        out = snapshot_at_time(time_db, as_of_ts=1500.0)
        ids = {e["id"] for e in out}
        assert ids == {"f1"}

    def test_snapshot_at_t2300_includes_f1_f2_f3(
        self, time_db: Path,
    ) -> None:
        """At ts=2300: f1 (always alive), f2 (created 2000, supersede
        2500 hasn't happened yet), f3 (created 2200) all alive.
        f4/f5 not created yet."""
        out = snapshot_at_time(time_db, as_of_ts=2300.0)
        ids = {e["id"] for e in out}
        assert ids == {"f1", "f2", "f3"}

    def test_snapshot_at_t2600_excludes_already_superseded_f2(
        self, time_db: Path,
    ) -> None:
        """At ts=2600 f2 has been superseded at 2500 → excluded."""
        out = snapshot_at_time(time_db, as_of_ts=2600.0)
        ids = {e["id"] for e in out}
        assert "f2" not in ids
        # f1, f3 still alive; f5 created at 2800 (not yet);
        # f4 created at 3000 (not yet)
        assert ids == {"f1", "f3"}

    def test_snapshot_at_far_future_includes_all_alive(
        self, time_db: Path,
    ) -> None:
        """ts=99999: f2 and f5 superseded; f1, f3, f4 alive."""
        out = snapshot_at_time(time_db, as_of_ts=99999.0)
        ids = {e["id"] for e in out}
        assert ids == {"f1", "f3", "f4"}

    def test_topic_filter_works(self, time_db: Path) -> None:
        out = snapshot_at_time(
            time_db, as_of_ts=99999.0, topic="t/b",
        )
        ids = {e["id"] for e in out}
        assert ids == {"f4"}

    def test_chronological_order(self, time_db: Path) -> None:
        out = snapshot_at_time(time_db, as_of_ts=99999.0)
        timestamps = [e["created_at"] for e in out]
        assert timestamps == sorted(timestamps)

    def test_limit_caps_result(self, time_db: Path) -> None:
        out = snapshot_at_time(time_db, as_of_ts=99999.0, limit=1)
        assert len(out) == 1

    def test_returns_required_fields(self, time_db: Path) -> None:
        out = snapshot_at_time(time_db, as_of_ts=99999.0)
        for e in out:
            for key in ("id", "proposition", "topic",
                         "created_at", "superseded_at"):
                assert key in e

    def test_empty_db_returns_empty(self, tmp_path: Path) -> None:
        db_path = tmp_path / "empty.db"
        conn = sqlite3.connect(str(db_path))
        conn.executescript(_SCHEMA)
        conn.close()
        out = snapshot_at_time(db_path, as_of_ts=1000.0)
        assert out == []
