"""TDD for benchmark/corpus_health_snapshot — real-corpus epistemic-health snapshot."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from benchmark.corpus_health_snapshot import snapshot


def _make_db(path: str, rows: list[tuple]) -> None:
    c = sqlite3.connect(path)
    c.execute("create table facts(id text, status text, superseded_by text, "
              "verified_by text, source_episodes text)")
    c.executemany("insert into facts values(?,?,?,?,?)", rows)
    c.commit()
    c.close()


def test_snapshot_counts(tmp_path: Path) -> None:
    db = str(tmp_path / "f.db")
    _make_db(db, [
        ("1", "verified", None, "commit:abc", "ep1"),
        ("2", "quarantined", None, None, None),
        ("3", "model_claim", None, "", "[]"),          # empty provenance -> not counted
        ("4", "verified", "5", "commit:x", "ep9"),     # superseded -> excluded from alive
    ])
    s = snapshot(db)
    assert s["total"] == 4
    assert s["alive"] == 3
    assert s["superseded"] == 1
    assert s["verified"] == 1                          # fact 4 is superseded
    assert s["with_verified_by"] == 1                  # only fact 1 (3 empty, 4 superseded)
    assert s["with_source_episodes"] == 1
    assert s["status_distribution"]["quarantined"] == 1
    assert s["verified_frac"] == round(1 / 3, 4)
