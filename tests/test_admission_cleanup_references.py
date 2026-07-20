"""Reference-aware retroactive telemetry cleanup (task #61, 2026-07-20).

The one-shot ``cleanup_telemetry`` predates the reference measurement done
today on the live corpus: of 291 ROUTE_TELEMETRY residues, 90 facts point
at some of them via ``superseded_by`` (deleting the target strands the
chain), and the ``contradictions`` table cites them in ~4.6k rows. Kimi-K3's
review predicted exactly this hole ("if a graph exists, the cleanup leaves
dangling references and P3 is no longer hygiene").

Contract driven here:
  - a telemetry fact that is the TARGET of another fact's ``superseded_by``
    is SKIPPED (conservative: never break a chain), counted in
    ``skipped_referenced``;
  - unreferenced telemetry moves, and the FTS index follows via the
    existing facts_fts_* triggers (proven, not assumed);
  - UNRESOLVED ``contradictions`` rows citing a moved fact are pruned
    (they are scan output, regenerable); RESOLVED rows are curated state
    and stay.
"""
from __future__ import annotations

import sqlite3

import pytest

from verimem.semantic import Fact, SemanticMemory

_CONTRA_DDL = """
CREATE TABLE IF NOT EXISTS contradictions (
    id TEXT PRIMARY KEY,
    fact_a_id TEXT NOT NULL,
    fact_b_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    similarity REAL NOT NULL,
    detected_at REAL NOT NULL,
    resolved_at REAL,
    resolution_note TEXT
)
"""


@pytest.fixture()
def dirty_db(tmp_path, monkeypatch):
    """A legacy corpus: telemetry already sitting in facts (gate off)."""
    monkeypatch.setenv("ENGRAM_ADMISSION_GATE", "0")
    db = tmp_path / "s.db"
    sm = SemanticMemory(db_path=db)
    sm.store(Fact(id="know1", proposition="real knowledge about deploys",
                  topic="lessons/deploy", source_episodes=["ep1"]))
    sm.store(Fact(id="tel_free", proposition="bus event unreferenced",
                  topic="bus/free"))
    sm.store(Fact(id="tel_target", proposition="bus event referenced",
                  topic="bus/target"))
    sm.store(Fact(id="know_old", proposition="old knowledge",
                  topic="lessons/deploy", source_episodes=["ep0"]))
    conn = sqlite3.connect(db)
    # FTS + triggers exactly as the product creates them (lazy, on first
    # keyword search) — the live DB has them, so the cleanup must be proven
    # against them, not against a bare schema.
    from verimem.bm25_rank import _ensure_fts
    _ensure_fts(conn)
    with conn:
        # know_old was superseded by tel_target -> tel_target must not move
        conn.execute(
            "UPDATE facts SET superseded_by='tel_target' WHERE id='know_old'")
        conn.execute(_CONTRA_DDL)
        conn.execute(
            "INSERT INTO contradictions VALUES "
            "('c_unres', 'tel_free', 'know1', 'numeric', 0.9, 1.0, NULL, NULL)")
        conn.execute(
            "INSERT INTO contradictions VALUES "
            "('c_res', 'tel_free', 'know1', 'numeric', 0.9, 1.0, 2.0, 'kept A')")
        conn.execute(
            "INSERT INTO contradictions VALUES "
            "('c_other', 'know1', 'know_old', 'date', 0.8, 1.0, NULL, NULL)")
    conn.close()
    return db


def _one(db, sql, *args):
    c = sqlite3.connect(db)
    try:
        return c.execute(sql, args).fetchone()[0]
    finally:
        c.close()


def test_dry_run_reports_references_without_mutating(dirty_db):
    from verimem.admission_cleanup import cleanup_telemetry

    res = cleanup_telemetry(dirty_db, dry_run=True)
    assert res["telemetry_found"] == 2
    assert res["skipped_referenced"] == 1
    assert res["moved"] == 0
    assert _one(dirty_db, "SELECT COUNT(*) FROM facts WHERE topic LIKE 'bus/%'") == 2
    assert _one(dirty_db, "SELECT COUNT(*) FROM contradictions") == 3


def test_referenced_supersession_target_is_skipped(dirty_db):
    from verimem.admission_cleanup import cleanup_telemetry

    res = cleanup_telemetry(dirty_db, dry_run=False)
    assert res["moved"] == 1
    assert res["skipped_referenced"] == 1
    # the chain target survives in facts; the unreferenced one moved
    assert _one(dirty_db, "SELECT COUNT(*) FROM facts WHERE id='tel_target'") == 1
    assert _one(dirty_db, "SELECT COUNT(*) FROM facts WHERE id='tel_free'") == 0
    assert _one(dirty_db, "SELECT COUNT(*) FROM telemetry WHERE id='tel_free'") == 1
    # no dangling superseded_by anywhere
    assert _one(
        dirty_db,
        "SELECT COUNT(*) FROM facts a WHERE a.superseded_by IS NOT NULL "
        "AND NOT EXISTS (SELECT 1 FROM facts b WHERE b.id=a.superseded_by)") == 0


def test_fts_follows_the_move(dirty_db):
    from verimem.admission_cleanup import cleanup_telemetry

    assert _one(dirty_db,
                "SELECT COUNT(*) FROM facts_fts WHERE fact_id='tel_free'") == 1
    cleanup_telemetry(dirty_db, dry_run=False)
    assert _one(dirty_db,
                "SELECT COUNT(*) FROM facts_fts WHERE fact_id='tel_free'") == 0


def test_unresolved_contradiction_rows_of_moved_are_pruned(dirty_db):
    from verimem.admission_cleanup import cleanup_telemetry

    res = cleanup_telemetry(dirty_db, dry_run=False)
    assert res["contradictions_pruned"] == 1
    # unresolved row citing the moved fact: gone
    assert _one(dirty_db, "SELECT COUNT(*) FROM contradictions WHERE id='c_unres'") == 0
    # resolved row is curated state: stays
    assert _one(dirty_db, "SELECT COUNT(*) FROM contradictions WHERE id='c_res'") == 1
    # row not citing any moved fact: stays
    assert _one(dirty_db, "SELECT COUNT(*) FROM contradictions WHERE id='c_other'") == 1


def test_db_without_contradictions_table_still_works(tmp_path, monkeypatch):
    from verimem.admission_cleanup import cleanup_telemetry

    monkeypatch.setenv("ENGRAM_ADMISSION_GATE", "0")
    db = tmp_path / "bare.db"
    sm = SemanticMemory(db_path=db)
    sm.store(Fact(id="t1", proposition="bus tick", topic="bus/x"))
    res = cleanup_telemetry(db, dry_run=False)
    assert res["moved"] == 1
    assert res["contradictions_pruned"] == 0
