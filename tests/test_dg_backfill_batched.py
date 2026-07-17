"""_backfill_dg_embeddings must not hold the write lock across the whole
O(N) loop (long-lock hunt #2, 2026-06-13).

Pre-fix it ran every UPDATE inside ONE `with self._connect()` (busy_timeout
60s), so on a v2-imported corpus the first DG recall held the episodes.db
write lock for the whole back-fill (~5s for 5k rows). A concurrent save in
that window stalled. Like backfill_pending_embeddings, the encode is read-
only w.r.t. the db, so the lock should cover only short per-batch UPDATEs.

Fix: compute dg_encode OUTSIDE the connection and commit in batches, so the
lock is released between batches and a concurrent writer slips in.

RED marker: pre-fix the whole back-fill runs under a single connection.
"""
from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path

import numpy as np

import verimem.memory as memmod
from verimem.episode import Episode

EpisodicMemory = memmod.EpisodicMemory  # single import style (CodeQL): the
# module is monkeypatched (memmod._DG_BACKFILL_BATCH / memmod.dg_encode) so we
# keep the `import ... as` form and alias the class from it.


def _seed_null_dg(mem: EpisodicMemory, n: int) -> None:
    """Store n episodes, then NULL their dg_embedding to force a back-fill."""
    for i in range(n):
        mem.store(Episode(id=f"dg-{i:04d}", task_text=f"episode number {i}",
                          final_answer="ans"), embed="sync")
    with sqlite3.connect(str(mem.db_path)) as c:
        c.execute("UPDATE episodes SET dg_embedding = NULL")
        c.commit()
    mem._dg_index = None
    mem._index_dirty = True


def test_backfill_correct_and_batched(tmp_path: Path, monkeypatch) -> None:
    db = tmp_path / "episodes" / "episodes.db"
    db.parent.mkdir(parents=True)
    mem = EpisodicMemory(db_path=db)
    _seed_null_dg(mem, 7)

    # Count connections opened during the back-fill: >1 proves batching
    # (a single monolithic txn would open exactly 1 for the whole loop).
    opens = {"n": 0}
    real_connect = sqlite3.connect

    def _counting(*a, **k):
        if a and "episodes.db" in str(a[0]):
            opens["n"] += 1
        return real_connect(*a, **k)

    monkeypatch.setattr(sqlite3, "connect", _counting)
    monkeypatch.setattr(memmod, "_DG_BACKFILL_BATCH", 2, raising=False)
    n = mem._backfill_dg_embeddings()

    assert n == 7, "every NULL-dg episode must be back-filled"
    assert opens["n"] >= 2, (
        f"back-fill must batch its writes (>1 connection), got {opens['n']} "
        "— a single connection holds the lock across the whole O(N) loop"
    )
    # correctness: no NULL dg left
    with sqlite3.connect(str(db)) as c:
        left = c.execute(
            "SELECT COUNT(*) FROM episodes WHERE dg_embedding IS NULL"
        ).fetchone()[0]
    assert left == 0


def test_backfill_idempotent_and_encode_outside_lock(tmp_path: Path, monkeypatch) -> None:
    """A re-run after a full back-fill writes nothing; and dg_encode runs
    while NO episodes.db write connection is open (encode outside the lock)."""
    db = tmp_path / "episodes" / "episodes.db"
    db.parent.mkdir(parents=True)
    mem = EpisodicMemory(db_path=db)
    _seed_null_dg(mem, 5)
    monkeypatch.setattr(memmod, "_DG_BACKFILL_BATCH", 2, raising=False)

    # Track open write-connections; assert dg_encode is never called while one
    # is held (it must be computed outside the lock).
    open_conns = {"n": 0}
    encode_under_lock = {"hit": False}
    real_connect = sqlite3.connect

    class _Tracking(sqlite3.Connection):
        def __enter__(self):
            open_conns["n"] += 1
            return super().__enter__()

        def __exit__(self, *a):
            open_conns["n"] -= 1
            return super().__exit__(*a)

    def _conn(*a, **k):
        if a and "episodes.db" in str(a[0]):
            k.setdefault("factory", _Tracking)
        return real_connect(*a, **k)

    real_dg = memmod.dg_encode

    def _watch_dg(emb, W, **kw):
        if open_conns["n"] > 0:
            encode_under_lock["hit"] = True
        return real_dg(emb, W, **kw)

    monkeypatch.setattr(sqlite3, "connect", _conn)
    monkeypatch.setattr(memmod, "dg_encode", _watch_dg)

    n1 = mem._backfill_dg_embeddings()
    assert n1 == 5
    assert not encode_under_lock["hit"], (
        "dg_encode must run OUTSIDE any held write connection"
    )
    n2 = mem._backfill_dg_embeddings()
    assert n2 == 0, "a second back-fill must be a no-op (idempotent)"
    _ = (np, threading, time)  # keep imports referenced
