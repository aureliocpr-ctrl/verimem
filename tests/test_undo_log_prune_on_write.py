"""Audit 2026-06-08 A8: prune_expired_undo_log (7-day TTL) had NO production
caller — list_undoable only HID expired rows (ttl filter) but never DELETEd
them, so facts_undo_log grew unbounded on the core semantic DB (a full
row+embedding JSON snapshot per forget). snapshot_pre_op now prunes expired
rows opportunistically on each write, bounding the table.
"""
from __future__ import annotations

import time

from verimem import undo_log
from verimem.semantic import Fact, SemanticMemory


def test_snapshot_pre_op_prunes_expired_rows(tmp_path):
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    sm.store(
        Fact(proposition="keep me alive", topic="x", status="model_claim",
             source_episodes=["e1"]),
        embed="defer",
    )
    with sm._connect() as conn:
        undo_log.ensure_undo_table(conn)
        fid = conn.execute(
            "SELECT id FROM facts WHERE proposition = 'keep me alive'"
        ).fetchone()[0]
        # An already-expired undo row (ttl in the past) — dead weight today.
        conn.execute(
            "INSERT INTO facts_undo_log (op_id, op_type, fact_id, pre_row_json, "
            "created_at, undone_at, ttl_expires_at) "
            "VALUES ('expired_op', 'forget', 'ghost', '{}', ?, NULL, ?)",
            (time.time() - 10_000, time.time() - 100),
        )
        conn.commit()

    with sm._connect() as conn:
        op_id = undo_log.snapshot_pre_op(conn, "forget", fid)
        conn.commit()
        n_expired = conn.execute(
            "SELECT COUNT(*) FROM facts_undo_log WHERE op_id = 'expired_op'"
        ).fetchone()[0]
        n_new = conn.execute(
            "SELECT COUNT(*) FROM facts_undo_log WHERE fact_id = ?", (fid,)
        ).fetchone()[0]

    assert op_id is not None, "snapshot should succeed for an existing fact"
    assert n_expired == 0, "expired undo row was NOT pruned (unbounded growth)"
    assert n_new == 1, "new snapshot not recorded"
