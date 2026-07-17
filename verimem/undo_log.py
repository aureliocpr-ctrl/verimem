"""Cycle 2026-05-27 round 13 P0c — transactional rollback for destructive ops.

Aurelio audit gap C5: "no transactional rollback su operazioni distruttive
(forget/supersede facts)".

Pattern: every destructive op writes a pre-state snapshot (full row JSON) to
``facts_undo_log`` BEFORE mutating the live row. ``undo_op(op_id)`` reads the
snapshot and restores it.

Schema v7 (added 2026-05-27 cycle 13):

    CREATE TABLE facts_undo_log (
        op_id TEXT PRIMARY KEY,
        op_type TEXT NOT NULL,          -- 'forget' | 'supersede' | 'modify'
        fact_id TEXT NOT NULL,
        pre_row_json TEXT NOT NULL,     -- full fact row as JSON
        created_at REAL NOT NULL,
        undone_at REAL,                  -- NULL if not yet undone
        ttl_expires_at REAL              -- created_at + 7 days
    );

TTL 7 giorni: after that the undo entry can be pruned (separate cleanup task).
The fact row itself is unaffected by undo log TTL.

API:
    snapshot_pre_op(conn, op_type, fact_id) -> op_id
    undo_op(conn, op_id) -> dict
    list_undoable(conn, limit=20) -> list[UndoEntry]
    prune_expired_undo_log(conn) -> int
"""
from __future__ import annotations

import json
import sqlite3
import time
import uuid
from dataclasses import dataclass
from typing import Literal

UNDO_TTL_SECONDS: int = 7 * 24 * 3600  # 7 days

OpType = Literal["forget", "supersede", "modify"]


@dataclass(frozen=True)
class UndoEntry:
    """One row from facts_undo_log."""
    op_id: str
    op_type: OpType
    fact_id: str
    pre_row: dict
    created_at: float
    undone_at: float | None
    ttl_expires_at: float


def ensure_undo_table(conn: sqlite3.Connection) -> None:
    """Create the facts_undo_log table if it doesn't exist.

    Called from semantic.py's migration ladder + lazily on first use.
    Idempotent.
    """
    conn.execute(
        """CREATE TABLE IF NOT EXISTS facts_undo_log (
            op_id TEXT PRIMARY KEY,
            op_type TEXT NOT NULL,
            fact_id TEXT NOT NULL,
            pre_row_json TEXT NOT NULL,
            created_at REAL NOT NULL,
            undone_at REAL,
            ttl_expires_at REAL NOT NULL
        )"""
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_facts_undo_fact_id "
        "ON facts_undo_log(fact_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_facts_undo_created_at "
        "ON facts_undo_log(created_at DESC)"
    )


# Cycle 14 FIX 5 (agy audit Medium undo_log.py:98 + 108-112).
# Typed envelope sentinel for byte columns. Pre-fix used the bare key
# ``__bytes_b64__``; if a user's proposition happened to contain that
# JSON key the restore would base64-decode arbitrary text into bytes,
# corrupting the row. Post-fix the envelope uses TWO sentinel fields
# (_undo_envelope=v1 + _type=bytes) so an accidental collision in
# user data is statistically impossible.
_ENVELOPE_TAG = "_undo_envelope"
_ENVELOPE_VERSION = "v1"


def _is_bytes_envelope(val) -> bool:
    return (
        isinstance(val, dict)
        and val.get(_ENVELOPE_TAG) == _ENVELOPE_VERSION
        and val.get("_type") == "bytes"
        and "val" in val
    )


def _row_to_dict(conn: sqlite3.Connection, fact_id: str) -> dict | None:
    """Serialize a single facts row to a dict, preserving all columns.

    Cycle 14 FIX 5: typed envelope for bytes columns (collision-safe).
    """
    cur = conn.cursor()
    cur.execute("SELECT * FROM facts WHERE id = ?", (fact_id,))
    row = cur.fetchone()
    if row is None:
        return None
    cols = [d[0] for d in cur.description]
    out: dict = {}
    for col, val in zip(cols, row, strict=False):
        if isinstance(val, bytes):
            import base64
            out[col] = {
                _ENVELOPE_TAG: _ENVELOPE_VERSION,
                "_type": "bytes",
                "val": base64.b64encode(val).decode("ascii"),
            }
        else:
            out[col] = val
    return out


def _dict_to_row_args(
    row_dict: dict,
    *,
    current_cols: set[str] | None = None,
) -> tuple[list[str], list]:
    """Inverse of _row_to_dict: produce (cols, values) for an INSERT.

    Cycle 14 FIX 5 (agy audit Medium): schema-tolerant restore. When
    ``current_cols`` is provided, only columns present in the live schema
    are emitted. Columns in the snapshot that no longer exist (post-
    migration drop) are silently skipped; columns in the live schema that
    were absent at snapshot time (post-migration add) are also skipped
    here — SQLite will fill them with the column's DEFAULT.

    This makes ``undo_op`` survive schema migrations between the original
    destructive op and the undo call.
    """
    cols: list[str] = []
    vals: list = []
    for col, val in row_dict.items():
        if current_cols is not None and col not in current_cols:
            # Column no longer exists in the live schema (post-drop or
            # post-rename); skip rather than crash.
            continue
        cols.append(col)
        if _is_bytes_envelope(val):
            import base64
            vals.append(base64.b64decode(val["val"]))
        else:
            vals.append(val)
    return cols, vals


def snapshot_pre_op(
    conn: sqlite3.Connection,
    op_type: OpType,
    fact_id: str,
) -> str | None:
    """Snapshot the fact row BEFORE a destructive op. Returns op_id.

    Returns None if the fact does not exist (no-op, nothing to undo).
    The caller should treat None as "no undo handle available" and skip
    snapshot_pre_op without aborting the parent operation.
    """
    pre_row = _row_to_dict(conn, fact_id)
    if pre_row is None:
        return None
    op_id = uuid.uuid4().hex[:16]
    now = time.time()
    conn.execute(
        """INSERT INTO facts_undo_log
           (op_id, op_type, fact_id, pre_row_json, created_at,
            undone_at, ttl_expires_at)
           VALUES (?, ?, ?, ?, ?, NULL, ?)""",
        (op_id, op_type, fact_id,
         json.dumps(pre_row, ensure_ascii=False),
         now, now + UNDO_TTL_SECONDS),
    )
    # A8 (audit 2026-06-08): bound the log — prune expired rows opportunistically
    # on each write. prune_expired_undo_log had NO production caller, so the
    # 7-day-TTL DELETE was dead code and facts_undo_log grew unbounded on the
    # core DB (a full row+embedding snapshot per forget). Best-effort: a prune
    # failure must never break creation of the undo handle.
    try:
        prune_expired_undo_log(conn)
    except sqlite3.Error:
        pass
    return op_id


def undo_op(conn: sqlite3.Connection, op_id: str) -> dict:
    """Restore the pre-op snapshot for op_id. Returns result dict.

    Result keys:
        ok: bool
        op_id: str
        op_type: str
        fact_id: str
        action: 'restored' | 'already_undone' | 'expired' | 'not_found'

    Restoration uses INSERT OR REPLACE so the row is recreated even if it
    was hard-deleted (forget) or modified (supersede). The undone_at column
    is stamped so re-undo is a no-op.
    """
    cur = conn.cursor()
    cur.execute(
        "SELECT op_type, fact_id, pre_row_json, undone_at, ttl_expires_at "
        "FROM facts_undo_log WHERE op_id = ?",
        (op_id,),
    )
    row = cur.fetchone()
    if row is None:
        return {"ok": False, "op_id": op_id, "action": "not_found"}
    op_type, fact_id, pre_row_json, undone_at, ttl = row
    if undone_at is not None:
        return {
            "ok": False, "op_id": op_id, "op_type": op_type,
            "fact_id": fact_id, "action": "already_undone",
            "undone_at": undone_at,
        }
    if time.time() > float(ttl):
        return {
            "ok": False, "op_id": op_id, "op_type": op_type,
            "fact_id": fact_id, "action": "expired",
            "ttl_expires_at": float(ttl),
        }
    pre_row = json.loads(pre_row_json)
    # Cycle 14 FIX 5: schema-tolerant restore. Query the live schema's
    # column set so columns added/removed by migrations between the op
    # and the undo don't break the restore.
    cur.execute("PRAGMA table_info(facts)")
    current_cols = {r[1] for r in cur.fetchall()}
    cols, vals = _dict_to_row_args(pre_row, current_cols=current_cols)
    placeholders = ",".join(["?"] * len(cols))
    col_list = ",".join(cols)
    conn.execute(
        f"INSERT OR REPLACE INTO facts ({col_list}) VALUES ({placeholders})",
        vals,
    )
    conn.execute(
        "UPDATE facts_undo_log SET undone_at = ? WHERE op_id = ?",
        (time.time(), op_id),
    )
    return {
        "ok": True, "op_id": op_id, "op_type": op_type,
        "fact_id": fact_id, "action": "restored",
    }


def list_undoable(
    conn: sqlite3.Connection, *, limit: int = 20,
) -> list[UndoEntry]:
    """Return the N most recent undoable ops (newest first, not yet undone,
    not yet expired)."""
    cur = conn.cursor()
    cur.execute(
        "SELECT op_id, op_type, fact_id, pre_row_json, "
        "created_at, undone_at, ttl_expires_at "
        "FROM facts_undo_log "
        "WHERE undone_at IS NULL AND ttl_expires_at > ? "
        "ORDER BY created_at DESC LIMIT ?",
        (time.time(), int(limit)),
    )
    out: list[UndoEntry] = []
    for r in cur.fetchall():
        out.append(UndoEntry(
            op_id=r[0], op_type=r[1], fact_id=r[2],
            pre_row=json.loads(r[3]),
            created_at=r[4], undone_at=r[5], ttl_expires_at=r[6],
        ))
    return out


def prune_expired_undo_log(conn: sqlite3.Connection) -> int:
    """Delete undo entries past their TTL. Returns count deleted."""
    cur = conn.execute(
        "DELETE FROM facts_undo_log WHERE ttl_expires_at < ?",
        (time.time(),),
    )
    return int(cur.rowcount)


__all__ = [
    "UNDO_TTL_SECONDS",
    "OpType",
    "UndoEntry",
    "ensure_undo_table",
    "snapshot_pre_op",
    "undo_op",
    "list_undoable",
    "prune_expired_undo_log",
]
