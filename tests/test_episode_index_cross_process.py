"""EpisodicMemory recall/DG indexes must invalidate on cross-process writes
(save/recall hunt #2, 2026-06-14).

The `_index_dirty` flag only catches same-instance mutations. Under N processes
sharing episodes.db, an external INSERT/DELETE left the cached in-RAM index stale
(stale rows served / new rows never recalled). Fix mirrors SemanticMemory: a
long-lived PRAGMA data_version probe, stamped per index, forces a rebuild when an
external connection commits.
"""
from __future__ import annotations

import sqlite3

from engram.memory import EpisodicMemory


def test_external_commit_diverges_index_stamp_then_rebuild_restamps(tmp_path):
    db = tmp_path / "ep.db"
    em = EpisodicMemory(db_path=db)

    # Build both indexes; their data_version stamp matches the live probe.
    em._ensure_recall_index()
    em._ensure_dg_index()
    assert em._index_dirty is False
    assert em._recall_index_dv == em._db_data_version()
    assert em._dg_index_dv == em._db_data_version()

    # A DIFFERENT connection commits (simulates another process writing the file).
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE _ext_marker (x INTEGER)")
    con.commit()
    con.close()

    live = em._db_data_version()
    # The cached stamps no longer match the live data_version → the cache-hit
    # guard fails and the index is treated stale (the whole point of the fix).
    assert em._recall_index_dv != live, "external write must diverge the recall stamp"
    assert em._dg_index_dv != live, "external write must diverge the DG stamp"

    # Re-running _ensure_* rebuilds and re-stamps to the current data_version.
    em._ensure_recall_index()
    em._ensure_dg_index()
    assert em._recall_index_dv == em._db_data_version()
    assert em._dg_index_dv == em._db_data_version()


def test_no_external_write_keeps_cache(tmp_path):
    """Same-instance steady state: no rebuild when nothing external changed."""
    db = tmp_path / "ep.db"
    em = EpisodicMemory(db_path=db)
    first = em._ensure_recall_index()
    # identity: the SAME cached tuple object is returned (cache hit, no rebuild)
    assert em._ensure_recall_index() is first


def test_probe_survives_and_recovers_from_error(tmp_path):
    db = tmp_path / "ep.db"
    em = EpisodicMemory(db_path=db)
    v = em._db_data_version()
    assert isinstance(v, int)
    # force a probe-connection error path, then confirm it recovers (reopens).
    if em._dv_conn is not None:
        em._dv_conn.close()  # next probe will hit sqlite3.Error or reopen cleanly
    assert isinstance(em._db_data_version(), int)
