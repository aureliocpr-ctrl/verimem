"""Cycle 196 (2026-05-23) — rank_list_builders tests.

RED marker: ``from engram.rank_list_builders import ...`` must fail
on master.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

# RED MARKER
from engram.rank_list_builders import (
    confidence_rank,
    recency_decayed_rank,
    recency_rank,
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS facts (
    id TEXT PRIMARY KEY,
    proposition TEXT,
    topic TEXT,
    confidence REAL DEFAULT 0.9,
    lineage_to TEXT,
    superseded_by TEXT,
    status TEXT DEFAULT 'model_claim',
    created_at REAL
);
"""


@pytest.fixture
def seeded_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "semantic.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript(_SCHEMA)
    rows = [
        # id, prop, topic, confidence, lineage_to, superseded_by, status, created_at
        ("f-old",     "p", "t/a", 0.5, None, None, "model_claim", 1000.0),
        ("f-mid",     "p", "t/a", 0.9, None, None, "model_claim", 2000.0),
        ("f-new",     "p", "t/a", 0.7, None, None, "model_claim", 3000.0),
        ("f-other",   "p", "t/b", 1.0, None, None, "model_claim", 2500.0),
        ("f-dead",    "p", "t/a", 1.0, None, "f-mid", "model_claim", 1500.0),
        ("f-orphaned","p", "t/a", 1.0, None, None, "orphaned",     2800.0),
    ]
    conn.executemany(
        "INSERT INTO facts (id, proposition, topic, confidence, lineage_to, "
        "superseded_by, status, created_at) VALUES (?,?,?,?,?,?,?,?)",
        rows,
    )
    conn.commit()
    conn.close()
    return db_path


class TestRecencyRank:
    def test_missing_db_returns_empty(self, tmp_path: Path) -> None:
        assert recency_rank(tmp_path / "nope.db") == []

    def test_newest_first(self, seeded_db: Path) -> None:
        out = recency_rank(seeded_db)
        # f-new (3000) > f-other (2500) > f-mid (2000) > f-old (1000)
        # f-dead excluded (superseded), f-orphaned excluded (status)
        assert out.index("f-new") < out.index("f-mid")
        assert out.index("f-mid") < out.index("f-old")

    def test_excludes_superseded_and_orphaned(self, seeded_db: Path) -> None:
        out = recency_rank(seeded_db)
        assert "f-dead" not in out
        assert "f-orphaned" not in out

    def test_topic_filter(self, seeded_db: Path) -> None:
        out = recency_rank(seeded_db, topic="t/b")
        assert out == ["f-other"]

    def test_limit_cap(self, seeded_db: Path) -> None:
        out = recency_rank(seeded_db, limit=2)
        assert len(out) <= 2


class TestConfidenceRank:
    def test_missing_db_returns_empty(self, tmp_path: Path) -> None:
        assert confidence_rank(tmp_path / "nope.db") == []

    def test_high_confidence_first(self, seeded_db: Path) -> None:
        out = confidence_rank(seeded_db)
        # f-other (1.0), f-mid (0.9), f-new (0.7), f-old (0.5)
        # f-dead/orphaned excluded
        assert out[0] == "f-other"
        assert out.index("f-mid") < out.index("f-new") < out.index("f-old")

    def test_excludes_superseded_and_orphaned(
        self, seeded_db: Path,
    ) -> None:
        out = confidence_rank(seeded_db)
        assert "f-dead" not in out
        assert "f-orphaned" not in out


class TestRecencyDecayedRank:
    def test_missing_db_returns_empty(self, tmp_path: Path) -> None:
        out = recency_decayed_rank(
            tmp_path / "nope.db", now=99999.0,
        )
        assert out == []

    def test_newest_first_under_decay(self, seeded_db: Path) -> None:
        out = recency_decayed_rank(
            seeded_db, now=4000.0, decay_curve="exp",
            half_life_days=1.0,
        )
        # With aggressive decay (1d half-life), the newest fact f-new
        # (ts=3000, age=1000s≈0.012d) dominates → near 1.0 score.
        # f-old (age=3000s≈0.035d) much smaller. f-new must rank first.
        assert out[0] == "f-new"

    def test_excludes_superseded(self, seeded_db: Path) -> None:
        out = recency_decayed_rank(seeded_db, now=4000.0)
        assert "f-dead" not in out
