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
# the read path, where it costs 45% of every recall. Measured by timing only the
# open and close inside four real recalls: 463 ms of 1025, across ~100-104
# connections per query, matching an independent count the night before (102:
# 71 on semantic.db + 31 on entity_kg.db).
#
# The cost is not the PRAGMA set. Dropping it saves 0.307 ms per connection —
# 31 ms in total, 3% — because journal_mode is persistent in the file and
# synchronous shares the same header cost with it, so removing either one buys
# nothing. The cost is the FIRST ACCESS on a fresh connection: reading the
# schema, preparing the statement, opening the WAL. connect+close with no query
# costs 0.347 ms; with one SELECT, 2.224 ms. It cannot be optimised, only
# avoided — by not paying it a hundred times per query.
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
    honours by issuing only PRAGMA and never DML — its docstring says so. Here
    the SELECTs are the point, so the guard is a ``rollback`` on the way out: it
    closes whatever a half-consumed cursor left open, and on a clean connection
    it costs nothing.

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
        _drop(cache, key, conn)
        raise
    else:
        try:
            # Guardia DIFENSIVA, e va detto: nel codice di oggi nessuna
            # lettura tiene vivo un cursore (`conn.execute(...).fetchone()` lo
            # scarta subito, chiudendo la transazione da se'), quindi non cura
            # un difetto attuale e nessun test la copre — una mutazione che la
            # rimuove non fa fallire niente. Resta perche' costa zero e perche'
            # il giorno che una lettura iteri parzialmente (`for row in cur`
            # interrotto) la read transaction resterebbe aperta: verificato che
            # SQLite in quel caso considera la connessione in transazione
            # (PRAGMA journal_mode solleva "from within a transaction") mentre
            # conn.in_transaction dice False, quindi il guasto sarebbe invisibile.
            conn.rollback()
        except sqlite3.Error:
            _drop(cache, key, conn)


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
