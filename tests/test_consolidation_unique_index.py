"""Cycle #157 (2026-05-19) — UNIQUE INDEX cross-process tests (implementation
of cycle 156 design doc raccomandazione A).

Cycle 156 opus design doc (docs/cycle156_unique_index_cross_process_design.md)
ha raccomandato l'alternativa A: partial UNIQUE INDEX su
``facts(topic) WHERE superseded_by IS NULL AND proposition LIKE
'AUTO-CLUSTER-MASTER%'``. SQLite 3.51.1 verificato runtime, partial
unique index supportato dal floor 3.8.0.

Questo file aggiunge:
  • TEST migration v3→v4 cleans pre-existing duplicates + creates UNIQUE
    INDEX su nuovo DB.
  • TEST that UNIQUE INDEX prevents duplicate master fact write
    (IntegrityError signature fail-fast cycle 156 §6).
  • TEST that ``_persist_master`` catches sqlite3.IntegrityError and
    returns gracefully (race-losing process semantic).

Cross-process subprocess test deferred to cycle 158 (Windows subprocess
path semantics + db_path coordination richiede setup non triviale).
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from verimem.semantic import Fact, SemanticMemory


@pytest.fixture
def sm(tmp_path: Path) -> SemanticMemory:
    return SemanticMemory(db_path=tmp_path / "sem.db")


def test_unique_index_v4_created_on_fresh_db(sm: SemanticMemory) -> None:
    """Cycle 157 v4 migration must create the partial UNIQUE INDEX on
    ``facts(topic)`` for auto-master rows. Verify via sqlite_master.
    """
    with sm._connect() as conn:  # noqa: SLF001
        rows = conn.execute(
            "SELECT name, sql FROM sqlite_master "
            "WHERE type = 'index' AND name = 'idx_facts_auto_master_unique'",
        ).fetchall()
    assert len(rows) == 1, (
        f"Cycle 157: idx_facts_auto_master_unique must exist after "
        f"v3→v4 migration. Got {len(rows)} rows."
    )
    ddl = rows[0]["sql"] or ""
    assert "UNIQUE" in ddl.upper()
    assert "topic" in ddl.lower()
    assert "AUTO-CLUSTER-MASTER" in ddl


def test_unique_index_enforces_single_live_master_per_topic(
    sm: SemanticMemory,
) -> None:
    """Cycle 157 invariant verification — fail-fast signature (cycle 156
    design doc §5.2), restored after the scan-68 NONNA fix.

    Storia: cycle 157 aveva osservato che ``sm.store`` usava
    ``INSERT OR REPLACE`` -> il partial UNIQUE INDEX era rispettato via
    REPLACE silenzioso (no raise). Lo scan-68 fix (2026-06-02) ha
    sostituito ``INSERT OR REPLACE`` con ``INSERT ... ON CONFLICT(id) DO
    UPDATE`` per evitare la resurrezione dei fatti superseded. Effetto:
    un secondo master live con stesso topic (id diverso) NON viene più
    sostituito silenziosamente ma viola il partial UNIQUE INDEX e solleva
    ``sqlite3.IntegrityError`` = fail-fast (come da design 156 §5.2).

    Questo è il comportamento CORRETTO e voluto: l'invariante "≤1 live
    master per topic" è enforced at-rest dall'index, e il path applicativo
    (``auto_consolidate``) cattura l'IntegrityError come race-losing
    graceful (vedi test_consolidation_unique_index_cross_process). Qui
    verifichiamo l'invariante a basso livello: ``store`` diretto del
    duplicato fa raise, e resta 1 sola riga master live.
    """
    f1 = Fact(
        proposition="AUTO-CLUSTER-MASTER project/test/dup — entry point",
        topic="project/test/dup/auto-MASTER",
        confidence=0.85,
        status="model_claim",
    )
    sm.store(f1)

    f2 = Fact(
        proposition="AUTO-CLUSTER-MASTER project/test/dup — second writer",
        topic="project/test/dup/auto-MASTER",
        confidence=0.85,
        status="model_claim",
    )
    # Fail-fast: il partial UNIQUE INDEX rifiuta il secondo master live.
    with pytest.raises(sqlite3.IntegrityError):
        sm.store(f2)

    # Invariante: exactly 1 live master row per il topic (f1, f2 scartato).
    with sm._connect() as conn:  # noqa: SLF001
        n = conn.execute(
            "SELECT COUNT(*) FROM facts "
            "WHERE topic = ? AND superseded_by IS NULL "
            "AND proposition LIKE 'AUTO-CLUSTER-MASTER%'",
            ("project/test/dup/auto-MASTER",),
        ).fetchone()[0]
    assert n == 1, (
        f"Cycle 157 partial UNIQUE INDEX deve garantire 1 live master "
        f"per topic. Got {n}."
    )


def test_unique_index_allows_non_master_facts(sm: SemanticMemory) -> None:
    """Cycle 157 partial index must NOT affect non-master facts.
    Multiple non-master facts on the same topic remain legal.
    """
    for i in range(3):
        sm.store(Fact(
            proposition=f"Regular fact #{i} on shared topic",
            topic="project/shared/normal",
            confidence=0.7,
            status="model_claim",
        ))
    with sm._connect() as conn:  # noqa: SLF001
        count = conn.execute(
            "SELECT COUNT(*) FROM facts WHERE topic = ?",
            ("project/shared/normal",),
        ).fetchone()[0]
    assert count == 3


def test_unique_index_allows_superseded_duplicates(
    sm: SemanticMemory,
) -> None:
    """Partial index ``WHERE superseded_by IS NULL`` — a master fact that
    has been superseded must NOT block a new live master for the same
    topic.
    """
    f_old = Fact(
        proposition="AUTO-CLUSTER-MASTER project/test/super — old",
        topic="project/test/super/auto-MASTER",
        confidence=0.85,
        status="model_claim",
    )
    sm.store(f_old)
    # Mark it superseded.
    with sm._connect() as conn:  # noqa: SLF001
        conn.execute(
            "UPDATE facts SET superseded_by = 'new-id', "
            "superseded_at = 999, superseded_reason = 'test' "
            "WHERE id = ?",
            (f_old.id,),
        )
        conn.commit()

    # Now a fresh master on the same topic must succeed.
    f_new = Fact(
        proposition="AUTO-CLUSTER-MASTER project/test/super — new live",
        topic="project/test/super/auto-MASTER",
        confidence=0.85,
        status="model_claim",
    )
    sm.store(f_new)  # must NOT raise IntegrityError


def test_migration_v3_to_v4_cleans_preexisting_duplicates(
    tmp_path: Path,
) -> None:
    """Migration must mark all-but-oldest as superseded BEFORE creating
    the UNIQUE INDEX. Otherwise the DDL would fail on a DB that has
    pre-existing dup masters (from pre-cycle 155 sessions).
    """
    db_path = tmp_path / "dup.db"
    # Seed manually a v3-shape DB with 2 duplicate masters by going
    # under the SemanticMemory layer.
    sm = SemanticMemory(db_path=db_path)
    f1 = Fact(
        proposition="AUTO-CLUSTER-MASTER project/legacy — dup1",
        topic="project/legacy/auto-MASTER",
        confidence=0.85,
        status="model_claim",
    )
    sm.store(f1)

    # Force a second master under the same topic BYPASSING the v4 unique
    # index: we drop the index, insert, then re-apply migration logic.
    with sm._connect() as conn:  # noqa: SLF001
        conn.execute("DROP INDEX IF EXISTS idx_facts_auto_master_unique")
        conn.commit()

    f2 = Fact(
        proposition="AUTO-CLUSTER-MASTER project/legacy — dup2",
        topic="project/legacy/auto-MASTER",
        confidence=0.85,
        status="model_claim",
    )
    sm.store(f2)

    # Sanity: 2 live duplicates exist.
    with sm._connect() as conn:  # noqa: SLF001
        n = conn.execute(
            "SELECT COUNT(*) FROM facts "
            "WHERE topic = ? AND superseded_by IS NULL",
            ("project/legacy/auto-MASTER",),
        ).fetchone()[0]
    assert n == 2, f"setup: must have 2 live duplicates, got {n}"

    # Now re-apply migration: re-trigger schema bootstrap.
    from verimem.semantic import _migrate_v3_to_v4
    with sm._connect() as conn:  # noqa: SLF001
        _migrate_v3_to_v4(conn)
        conn.commit()

    # Post-migration: exactly 1 live + 1 superseded.
    with sm._connect() as conn:  # noqa: SLF001
        live = conn.execute(
            "SELECT COUNT(*) FROM facts "
            "WHERE topic = ? AND superseded_by IS NULL",
            ("project/legacy/auto-MASTER",),
        ).fetchone()[0]
        superseded = conn.execute(
            "SELECT COUNT(*) FROM facts "
            "WHERE topic = ? AND superseded_by IS NOT NULL",
            ("project/legacy/auto-MASTER",),
        ).fetchone()[0]
    assert live == 1, f"post-migration: 1 live expected, got {live}"
    assert superseded == 1, (
        f"post-migration: 1 superseded expected, got {superseded}"
    )
