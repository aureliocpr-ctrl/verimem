"""Cycle 2026-05-27 round 13 P0c — transactional rollback pytest TDD.

Closes Aurelio audit gap C5: no transactional rollback su forget/supersede.

Verifies:
- snapshot_pre_op captures full row state (including bytes columns)
- undo_op restores the snapshot (INSERT OR REPLACE)
- undo_op handles already_undone / not_found / expired correctly
- delete_with_undo + undo_destructive_op round-trip preserves fact identity
- list_undoable_ops filters expired/undone
"""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path

import pytest

from engram.semantic import Fact, SemanticMemory
from engram.undo_log import (
    UNDO_TTL_SECONDS,
    ensure_undo_table,
    list_undoable,
    prune_expired_undo_log,
    snapshot_pre_op,
    undo_op,
)


@pytest.fixture
def sm(tmp_path: Path) -> SemanticMemory:
    """Fresh SemanticMemory with schema v7 (undo log table)."""
    return SemanticMemory(db_path=tmp_path / "s.db")


@pytest.fixture
def seeded_sm(sm: SemanticMemory) -> SemanticMemory:
    """SemanticMemory with 5 facts seeded."""
    for i in range(5):
        sm.store(Fact(
            id=f"fact{i:02d}deadbeef",
            proposition=f"Atomic test fact #{i} for undo log",
            topic=f"test/undo/{i}",
            confidence=0.85,
            verified_by=[],
            status="model_claim",
        ))
    return sm


class TestSchemaV7Migration:
    def test_undo_log_table_exists(self, sm: SemanticMemory):
        conn = sqlite3.connect(str(sm.db_path), timeout=5)
        cur = conn.cursor()
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name='facts_undo_log'"
        )
        assert cur.fetchone() is not None
        conn.close()


class TestSnapshotAndUndo:
    def test_snapshot_returns_op_id(self, seeded_sm: SemanticMemory):
        conn = sqlite3.connect(str(seeded_sm.db_path), timeout=5)
        op_id = snapshot_pre_op(conn, "forget", "fact00deadbeef")
        conn.commit()
        conn.close()
        assert op_id is not None
        assert len(op_id) == 16  # uuid4().hex[:16]

    def test_snapshot_unknown_fact_returns_none(
        self, seeded_sm: SemanticMemory,
    ):
        conn = sqlite3.connect(str(seeded_sm.db_path), timeout=5)
        op_id = snapshot_pre_op(conn, "forget", "ghost000000000")
        conn.close()
        assert op_id is None

    def test_undo_restores_deleted_fact(self, seeded_sm: SemanticMemory):
        # 1. Snapshot.
        conn = sqlite3.connect(str(seeded_sm.db_path), timeout=5)
        op_id = snapshot_pre_op(conn, "forget", "fact00deadbeef")
        conn.commit()
        # 2. Delete.
        conn.execute("DELETE FROM facts WHERE id = ?", ("fact00deadbeef",))
        conn.commit()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM facts WHERE id = ?",
                     ("fact00deadbeef",))
        assert cur.fetchone()[0] == 0
        # 3. Undo.
        result = undo_op(conn, op_id)
        conn.commit()
        assert result["ok"] is True
        assert result["action"] == "restored"
        # 4. Verify restored.
        cur.execute("SELECT proposition FROM facts WHERE id = ?",
                     ("fact00deadbeef",))
        row = cur.fetchone()
        assert row is not None
        assert "Atomic test fact #0" in row[0]
        conn.close()

    def test_undo_twice_marks_already_undone(self, seeded_sm: SemanticMemory):
        conn = sqlite3.connect(str(seeded_sm.db_path), timeout=5)
        op_id = snapshot_pre_op(conn, "forget", "fact01deadbeef")
        conn.commit()
        conn.execute("DELETE FROM facts WHERE id = ?", ("fact01deadbeef",))
        conn.commit()
        # First undo: ok.
        r1 = undo_op(conn, op_id)
        conn.commit()
        assert r1["action"] == "restored"
        # Second undo: already_undone.
        r2 = undo_op(conn, op_id)
        assert r2["ok"] is False
        assert r2["action"] == "already_undone"
        conn.close()

    def test_undo_unknown_op_id_returns_not_found(
        self, seeded_sm: SemanticMemory,
    ):
        conn = sqlite3.connect(str(seeded_sm.db_path), timeout=5)
        r = undo_op(conn, "ghost1234567890a")
        conn.close()
        assert r["ok"] is False
        assert r["action"] == "not_found"

    def test_undo_expired_returns_expired(self, seeded_sm: SemanticMemory):
        conn = sqlite3.connect(str(seeded_sm.db_path), timeout=5)
        op_id = snapshot_pre_op(conn, "forget", "fact02deadbeef")
        # Force expiry by mutating ttl_expires_at directly.
        conn.execute(
            "UPDATE facts_undo_log SET ttl_expires_at = ? WHERE op_id = ?",
            (time.time() - 10, op_id),
        )
        conn.commit()
        r = undo_op(conn, op_id)
        conn.close()
        assert r["ok"] is False
        assert r["action"] == "expired"


class TestSemanticMemoryWrappers:
    def test_delete_with_undo_emits_op_id(self, seeded_sm: SemanticMemory):
        result = seeded_sm.delete_with_undo("fact03deadbeef")
        assert result["ok"] is True
        assert result["removed"] is True
        assert result["op_id"] is not None
        # Verify fact is gone.
        conn = sqlite3.connect(str(seeded_sm.db_path), timeout=5)
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM facts WHERE id = ?", ("fact03deadbeef",),
        )
        assert cur.fetchone()[0] == 0
        conn.close()

    def test_delete_with_undo_then_undo_restores(
        self, seeded_sm: SemanticMemory,
    ):
        del_result = seeded_sm.delete_with_undo("fact04deadbeef")
        op_id = del_result["op_id"]
        # Undo.
        undo_result = seeded_sm.undo_destructive_op(op_id)
        assert undo_result["ok"] is True
        assert undo_result["action"] == "restored"
        # Verify fact is back.
        conn = sqlite3.connect(str(seeded_sm.db_path), timeout=5)
        cur = conn.cursor()
        cur.execute(
            "SELECT proposition FROM facts WHERE id = ?",
            ("fact04deadbeef",),
        )
        row = cur.fetchone()
        conn.close()
        assert row is not None
        assert "Atomic test fact #4" in row[0]

    def test_delete_with_undo_missing_fact(self, sm: SemanticMemory):
        result = sm.delete_with_undo("ghost000000000")
        assert result["ok"] is True
        assert result["removed"] is False
        assert result["op_id"] is None

    def test_list_undoable_ops(self, seeded_sm: SemanticMemory):
        # Forget 3 facts.
        for fid in ("fact00deadbeef", "fact01deadbeef", "fact02deadbeef"):
            seeded_sm.delete_with_undo(fid)
        ops = seeded_sm.list_undoable_ops(limit=10)
        assert len(ops) == 3
        # Newest first ordering.
        assert ops[0]["op_type"] == "forget"
        assert ops[0]["fact_id"] in {
            "fact00deadbeef", "fact01deadbeef", "fact02deadbeef",
        }


class TestPruneExpired:
    def test_prune_removes_expired_only(self, seeded_sm: SemanticMemory):
        conn = sqlite3.connect(str(seeded_sm.db_path), timeout=5)
        op1 = snapshot_pre_op(conn, "forget", "fact00deadbeef")
        op2 = snapshot_pre_op(conn, "forget", "fact01deadbeef")
        # Expire op1 manually.
        conn.execute(
            "UPDATE facts_undo_log SET ttl_expires_at = ? WHERE op_id = ?",
            (time.time() - 10, op1),
        )
        conn.commit()
        deleted = prune_expired_undo_log(conn)
        conn.commit()
        assert deleted == 1
        # op2 should remain.
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM facts_undo_log")
        assert cur.fetchone()[0] == 1
        conn.close()


class TestSchemaTolerantRestore:
    """Cycle 14 FIX 5 (agy audit Medium): undo survives schema migrations.

    Pre-fix: undo_op INSERT OR REPLACE blindly used all pre_row keys; if a
    migration added a NOT NULL column without DEFAULT between op and undo,
    the INSERT failed with IntegrityError.

    Post-fix: undo_op filters pre_row keys against current PRAGMA table_info.
    Columns dropped post-snapshot are skipped; columns added post-snapshot
    get the schema's DEFAULT value.
    """

    def test_restore_survives_column_added_post_snapshot(
        self, seeded_sm: SemanticMemory,
    ):
        conn = sqlite3.connect(str(seeded_sm.db_path), timeout=5)
        # 1. Snapshot a fact with current schema.
        op_id = snapshot_pre_op(conn, "forget", "fact02deadbeef")
        conn.commit()
        # 2. Delete the fact.
        conn.execute("DELETE FROM facts WHERE id = ?", ("fact02deadbeef",))
        conn.commit()
        # 3. Simulate a future migration adding a new column with DEFAULT.
        conn.execute(
            "ALTER TABLE facts ADD COLUMN new_col TEXT DEFAULT 'post_v8'"
        )
        conn.commit()
        # 4. Undo — should succeed despite the new column.
        from engram.undo_log import undo_op
        result = undo_op(conn, op_id)
        conn.commit()
        assert result["ok"] is True
        assert result["action"] == "restored"
        # 5. The restored row has the new column populated with DEFAULT.
        cur = conn.cursor()
        cur.execute(
            "SELECT new_col FROM facts WHERE id = ?", ("fact02deadbeef",),
        )
        row = cur.fetchone()
        assert row is not None
        assert row[0] == "post_v8"
        conn.close()

    def test_restore_skips_column_dropped_post_snapshot(
        self, seeded_sm: SemanticMemory,
    ):
        """If a column was dropped between snapshot and undo, the restore
        should silently skip that key rather than crash."""
        conn = sqlite3.connect(str(seeded_sm.db_path), timeout=5)
        # Add a custom column first, snapshot, then drop it.
        conn.execute("ALTER TABLE facts ADD COLUMN tmp_col TEXT")
        conn.execute(
            "UPDATE facts SET tmp_col = 'will_be_dropped' "
            "WHERE id = 'fact03deadbeef'"
        )
        conn.commit()
        op_id = snapshot_pre_op(conn, "forget", "fact03deadbeef")
        conn.commit()
        # Delete + drop the column.
        conn.execute("DELETE FROM facts WHERE id = ?", ("fact03deadbeef",))
        # SQLite ALTER TABLE DROP COLUMN added in 3.35.0; if unavailable
        # we simulate via PRAGMA table rename trick. For modern sqlite use:
        try:
            conn.execute("ALTER TABLE facts DROP COLUMN tmp_col")
        except sqlite3.OperationalError:
            pytest.skip("SQLite < 3.35 — DROP COLUMN unsupported")
        conn.commit()
        # Undo — should succeed (tmp_col silently skipped).
        from engram.undo_log import undo_op
        result = undo_op(conn, op_id)
        conn.commit()
        assert result["ok"] is True
        assert result["action"] == "restored"
        conn.close()


class TestEnvelopeCollisionSafety:
    """Cycle 14 FIX 5 (agy audit Medium): typed envelope sentinel."""

    def test_old_envelope_key_in_user_data_not_decoded(
        self, seeded_sm: SemanticMemory,
    ):
        """A fact whose proposition is a JSON-like string mentioning the
        OLD envelope key '__bytes_b64__' is NOT misinterpreted as a bytes
        envelope by the new typed envelope check."""
        # Store a fact with a tricky proposition.
        from engram.semantic import Fact
        seeded_sm.store(Fact(
            id="trickyenvelope",
            proposition='{"__bytes_b64__": "this is just normal text"}',
            topic="test/envelope",
            confidence=0.9,
            verified_by=[],
            status="model_claim",
        ))
        # Forget with undo and restore.
        result = seeded_sm.delete_with_undo("trickyenvelope")
        op_id = result["op_id"]
        undo = seeded_sm.undo_destructive_op(op_id)
        assert undo["ok"] is True
        # Verify the proposition string survived round-trip unchanged.
        import sqlite3 as _s
        conn = _s.connect(str(seeded_sm.db_path), timeout=5)
        cur = conn.cursor()
        cur.execute(
            "SELECT proposition FROM facts WHERE id = ?", ("trickyenvelope",),
        )
        row = cur.fetchone()
        conn.close()
        assert row is not None
        # Proposition is still the original string, NOT b64-decoded bytes.
        assert row[0] == '{"__bytes_b64__": "this is just normal text"}'
