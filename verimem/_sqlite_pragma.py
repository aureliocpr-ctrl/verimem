"""Single source of truth for the SQLite connection PRAGMA policy.

The four DB modules (semantic, memory/episodic, entity_kg, skill) each open
short-lived per-operation connections with the same PRAGMA set (WAL +
busy_timeout=60000 + synchronous=NORMAL + foreign_keys). The ``synchronous`` level
was hard-coded in 5 places; this centralizes the ONE knob a deployment may want to
tune (production-scaling review 2026-06-20).

``synchronous=NORMAL`` (default) is WAL-safe and fast but, between checkpoints, a
committed-but-uncheckpointed write can be lost on an OS crash / power loss.
``ENGRAM_SQLITE_SYNCHRONOUS=FULL`` trades write throughput for per-commit fsync
durability — for deployments that need it. Default keeps current behaviour.
"""
from __future__ import annotations

import contextlib
import os
import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


def synchronous_mode() -> str:
    """Return the SQLite ``synchronous`` level: 'NORMAL' (default) or 'FULL'."""
    v = os.environ.get("ENGRAM_SQLITE_SYNCHRONOUS", "NORMAL").strip().upper()
    return "FULL" if v == "FULL" else "NORMAL"


# --- Read-only reuse (2026-07-26) --------------------------------------------
# The short-lived-per-operation policy above is right for writes and wrong for
# the read path, which opened 102 connections per query — counted, not
# estimated: 71 on semantic.db + 31 on entity_kg.db.
#
# The cost is not the PRAGMA set. Dropping it saves 0.307 ms per connection —
# 31 ms in total, 3% — because journal_mode is persistent in the file and
# synchronous shares the same header cost with it, so removing either one buys
# nothing. The cost is the FIRST ACCESS on a fresh connection: reading the
# schema, preparing the statement, opening the WAL. connect+close with no query
# costs 0.347 ms; with one SELECT, 2.224 ms. It cannot be optimised, only
# avoided — by not paying it a hundred times per query.
#
# So 102 x 2.224 = 227 ms of a 686.9 ms recall, 33%. Counted connections
# afterwards: 5 per query, 11 ms, 2.7%. An earlier version of this comment said
# 45%, from timing only open-and-close inside four recalls — that instrument was
# a contextmanager wrapped around _connect, so it also measured itself. The
# figure above is arithmetic over two independently counted quantities instead.
#
# SCOPE POLICY (sweep 2026-07-26 evening, live AST inventory: 93 read-only
# blocks / 101 with writes across verimem/). WIRED: the recall hot path
# (measured, 102 -> 5 connections/query) and every pure reader in entity_kg.py
# — except _get_graph, which STREAMS ~81k edges with no LIMIT and therefore
# keeps its own short-lived connection, per this module's docstring. NOT wired,
# by policy: the ~84 remaining cold read blocks (CLI stats, audits, dedup and
# admin tools). Each would save ~2.2 ms on a rare invocation, while the edits
# span 23 files and the classifier cannot prove blocks that hand their
# connection to helpers (an undo classified "read-only" is the counterexample).
# Judgment over churn: wiring them trades real edit risk for microseconds.
#
# WHY 5 AND NOT 1, and it is the load-bearing caveat: the reuse is per THREAD,
# and the read path creates a NEW thread per query (semantic.py, hippo-rerank
# and hippo-ppr-fusion). So the ~63 reads inside one query collapse onto 4-5
# connections — that is where the 227 ms went — and then the thread dies and the
# next query starts over. Counted: 5 per query, flat across six queries, with 51
# of 66 opened by the hippo-* threads and the MainThread's two lasting its whole
# life. Making them survive would need persistent workers or a shared pool, for
# the 11 ms that are left: not worth the machinery, but it must not be described
# as "one connection instead of a hundred" — it is five per query, every query.
_LOCAL = threading.local()


@contextmanager
def read_connection(db_path: Path | str) -> Iterator[sqlite3.Connection]:
    """A per-thread, reused, READ-ONLY connection.

    Per THREAD, not shared: sqlite3 refuses a connection used from another
    thread, and the read path works in threads (rerank, fusion). One shared
    connection behind a lock would also serialise reads that run in parallel
    today.

    Reads only. Writes keep their short-lived connection: that policy exists so
    a commit's fsync and its rollback window stay confined to one operation,
    and a long-lived writer would hold both open across unrelated work.

    THE CONSTRAINT THAT SHAPES THIS: a long-lived reader that leaves a read
    transaction open STARVES THE WAL CHECKPOINTS, and the file then grows with
    no way to consolidate. It is the same constraint ``_db_data_version``
    honours by issuing only PRAGMA and never DML — its docstring says so.

    AND NOTHING THIS FUNCTION CAN DO WOULD ENFORCE IT, which is why it does not
    pretend to. An earlier version ended with ``conn.rollback()`` and a comment
    saying it "closes whatever a half-consumed cursor left open". That was
    false. Measured on 2026-07-26, one observation per fresh database because
    ``PRAGMA journal_mode`` mutates what it is used to detect: with a live
    cursor mid-result, ``rollback()``, ``commit()``, ``interrupt()`` and raw
    ``ROLLBACK``/``COMMIT``/``END`` ALL leave the transaction open — the last
    three refuse outright with "no transaction is active". Only ``cur.close()``
    ends it. The read is not held by the driver's transaction, it is held by an
    unfinalized STATEMENT, and only the cursor's owner can finalize it.

    So the invariant lives with the CALLERS: every reader must let its cursor
    die inside the block — ``conn.execute(...).fetchone()`` /
    ``.fetchall()`` on a temporary, never ``cur = conn.execute(...)`` kept in a
    local. All six readers do, verified on the AST by
    ``test_no_reader_keeps_a_cursor_alive`` rather than left to discipline. A
    caller that needs partial iteration must open its own short-lived
    connection instead of this one.

    A connection that fails is dropped rather than kept: caching a broken one
    would turn a transient fault into a permanent one for that thread.
    """
    cache = getattr(_LOCAL, "conns", None)
    if cache is None:
        cache = _LOCAL.conns = {}
    key = str(db_path)
    conn = cache.get(key)
    if conn is not None and not _usable(conn):
        # checked BEFORE handing it over, not after: noticing on the caller's
        # first query would mean raising at them instead of quietly replacing a
        # dead connection. Measured at 0.00287 ms on a warm connection — 0.287 ms
        # across the ~100 reads of a recall, 0.03% of it, against ~460 ms saved.
        _drop(cache, key, conn)
        conn = None
    if conn is None:
        conn = sqlite3.connect(db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        # busy_timeout is per-connection and measured free (-0.029 ms); the
        # other two are not needed for reading — journal_mode is already in the
        # file and synchronous only governs write fsync.
        with contextlib.suppress(sqlite3.Error):
            conn.execute("PRAGMA busy_timeout=60000;")
        cache[key] = conn
    try:
        yield conn
    except sqlite3.Error:
        # a broken connection is dropped; every other exception is the caller's
        # business and leaves the connection cached, because it says nothing
        # about the connection's health.
        _drop(cache, key, conn)
        raise


def _usable(conn: sqlite3.Connection) -> bool:
    """Whether a cached connection still answers."""
    try:
        conn.execute("SELECT 1").fetchone()
        return True
    except Exception:  # noqa: BLE001 — a closed connection raises
        return False   # ProgrammingError, a broken file sqlite3.Error


def _drop(cache: dict, key: str, conn: sqlite3.Connection) -> None:
    cache.pop(key, None)
    with contextlib.suppress(sqlite3.Error):
        conn.close()


def close_read_connections() -> None:
    """Close this thread's reused readers (tests, shutdown)."""
    cache = getattr(_LOCAL, "conns", None) or {}
    for conn in list(cache.values()):
        with contextlib.suppress(sqlite3.Error):
            conn.close()
    cache.clear()


__all__ = ["close_read_connections", "read_connection", "synchronous_mode"]
