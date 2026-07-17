"""bump-on-recall must never block recall on a contended writer (2026-06-13).

Bug-hunt finding F3: _bump_verified issues an UPDATE on EVERY recall that
returns hits, on a connection that inherits busy_timeout=60000. Under a
held write lock (consolidation / dream / another session) the UPDATE
waits up to 60s, and it runs synchronously inside recall() before
returning — so the whole recall blocks ~60s. The encode and the rerank
already have wall-clock breakers precisely so recall never blocks; the
bump re-introduced an unbounded write wait.

Fix: the bump connection uses a SHORT busy_timeout
(HIPPO_BUMP_BUSY_TIMEOUT_MS, default 500) so a contended lock fails fast
and is swallowed (best-effort), leaving recall responsive.

RED marker: pre-fix, recall under a held write lock takes ~the default
busy_timeout; the short bump timeout caps it.
"""
from __future__ import annotations

import sqlite3
import threading
import time

from verimem.semantic import _BUMP_REFRESH_THRESHOLD_S, Fact, SemanticMemory

_QUERY = "the recall path ranks facts by cosine"


def _seed(sm: SemanticMemory) -> None:
    # Age past the bump refresh threshold (so the bump WHERE selects the row)
    # but well within the freshness half-life (so recall does NOT stale-filter
    # it out). threshold = 0.5*half_life, stale-cutoff = half_life, so
    # threshold + 1 day sits comfortably between them.
    old = time.time() - (_BUMP_REFRESH_THRESHOLD_S + 86400)
    for i, p in enumerate([
        "the recall path ranks facts by cosine over embeddings",
        "skills are consolidated during the dream rem stage",
        "sqlite uses write-ahead logging for concurrency",
    ]):
        sm.store(Fact(proposition=p, topic=f"t/{i}", source_episodes=["e"],
                      created_at=old), embed="sync")


def _hold_write_lock(db_path, started: threading.Event, release: threading.Event):
    """Hold the SQLite write lock via BEGIN IMMEDIATE until told to release."""
    conn = sqlite3.connect(str(db_path), timeout=30)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("BEGIN IMMEDIATE")
    conn.execute(
        "UPDATE facts SET confidence = confidence WHERE id = "
        "(SELECT id FROM facts LIMIT 1)"
    )
    started.set()
    release.wait(timeout=30)
    conn.rollback()
    conn.close()


def test_recall_not_blocked_by_bump_under_held_lock(tmp_path, monkeypatch):
    db = tmp_path / "s.db"
    sm = SemanticMemory(db_path=db)
    _seed(sm)
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", "0")   # isolate the bump cost
    monkeypatch.setenv("ENGRAM_BUMP_ON_RECALL", "1")  # bump ON (default)
    monkeypatch.setenv("HIPPO_BUMP_BUSY_TIMEOUT_MS", "500")

    started, release = threading.Event(), threading.Event()
    holder = threading.Thread(
        target=_hold_write_lock, args=(db, started, release), daemon=True)
    holder.start()
    assert started.wait(timeout=10), "lock holder failed to start"

    try:
        t0 = time.perf_counter()
        hits = sm.recall(_QUERY, k=5)
        elapsed = time.perf_counter() - t0
    finally:
        release.set()
        holder.join(timeout=10)

    assert elapsed < 3.0, (
        f"recall blocked {elapsed:.1f}s on the bump UPDATE under a held "
        f"write lock (bump must fail fast, not wait the 60s busy_timeout)"
    )
    assert hits, "recall must still return its hits despite a skipped bump"


def test_bump_writes_when_uncontended(tmp_path, monkeypatch):
    """No contention -> the bump still refreshes last_verified_at."""
    db = tmp_path / "s.db"
    sm = SemanticMemory(db_path=db)
    _seed(sm)
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", "0")
    monkeypatch.setenv("ENGRAM_BUMP_ON_RECALL", "1")

    before = {}
    with sqlite3.connect(str(db)) as c:
        for fid, lv in c.execute("SELECT id, last_verified_at FROM facts"):
            before[fid] = lv

    hits = sm.recall(_QUERY, k=5)
    assert hits
    time.sleep(0.1)
    with sqlite3.connect(str(db)) as c:
        after = dict(c.execute("SELECT id, last_verified_at FROM facts"))
    bumped = [fid for fid in before if after.get(fid, 0) > (before[fid] or 0)]
    assert bumped, "an uncontended bump must refresh at least one returned fact"


def test_bump_opt_out_skips_update(tmp_path, monkeypatch):
    db = tmp_path / "s.db"
    sm = SemanticMemory(db_path=db)
    _seed(sm)
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", "0")
    monkeypatch.setenv("ENGRAM_BUMP_ON_RECALL", "0")  # opt-out

    with sqlite3.connect(str(db)) as c:
        before = dict(c.execute("SELECT id, last_verified_at FROM facts"))
    sm.recall(_QUERY, k=5)
    with sqlite3.connect(str(db)) as c:
        after = dict(c.execute("SELECT id, last_verified_at FROM facts"))
    assert before == after, "opt-out must write nothing"
