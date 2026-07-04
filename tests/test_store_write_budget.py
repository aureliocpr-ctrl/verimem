"""Bounded interactive save — the second independent root of the recurring
save-block (proven 2026-06-06): SQLite is WAL + busy_timeout=60000, so when a
long background write (consolidation BEGIN IMMEDIATE, bulk store, another
session) holds the write lock, a concurrent `hippo_remember` store() WAITS up to
60s on the lock. Empirically reproduced: a concurrent writer waited 3.77s while a
holder held the lock 4s.

Cure (mirrors the encode circuit-breaker): `store_within_budget` runs the write
on a daemon thread and returns `deferred=True` if it can't finish within the
budget — the interactive caller NEVER blocks more than the budget, and the write
is NOT lost (the background thread completes it with the full busy_timeout).
"""
from __future__ import annotations

import sqlite3
import threading
import time

import numpy as np
import pytest

from engram.semantic import Fact, SemanticMemory


@pytest.fixture(autouse=True)
def _fast_encode(monkeypatch):
    # Isolate the WRITE-lock behavior from embedding latency: stub encode so the
    # only thing that can be slow in store() is the SQLite write lock.
    from engram import embedding
    monkeypatch.setattr(embedding, "encode", lambda *_a, **_k: np.ones(768, dtype=np.float32))
    monkeypatch.setattr(embedding, "_encode_one", lambda *_a, **_k: np.ones(768, dtype=np.float32))


def _hold_write_lock(db_path, hold_s, started: threading.Event, release: threading.Event):
    conn = sqlite3.connect(str(db_path), timeout=30)
    conn.execute("PRAGMA busy_timeout=60000")
    conn.execute("BEGIN IMMEDIATE")
    conn.execute("UPDATE facts SET topic='held' WHERE id='seed'")
    started.set()
    release.wait(timeout=hold_s)
    conn.commit()
    conn.close()


def test_store_within_budget_defers_when_write_lock_held(tmp_path):
    from engram.semantic import store_within_budget

    db = tmp_path / "sem.db"
    sm = SemanticMemory(db_path=db)
    sm.store(Fact(id="seed", proposition="seed fact", topic="t"))

    started, release = threading.Event(), threading.Event()
    holder = threading.Thread(
        target=_hold_write_lock, args=(db, 30.0, started, release), daemon=True,
    )
    holder.start()
    assert started.wait(timeout=5), "holder failed to acquire the write lock"

    try:
        t0 = time.time()
        res = store_within_budget(
            sm, Fact(id="f2", proposition="second fact", topic="t"), budget_s=2.0,
        )
        dt = time.time() - t0
        # The interactive caller must NOT block the full 60s busy_timeout.
        assert dt < 5.0, f"store_within_budget blocked {dt:.1f}s — not bounded"
        assert res.get("deferred") is True, f"expected deferred under lock, got {res}"
    finally:
        release.set()
        holder.join(timeout=5)


def test_store_within_budget_writes_normally_without_contention(tmp_path):
    from engram.semantic import store_within_budget

    sm = SemanticMemory(db_path=tmp_path / "sem.db")
    res = store_within_budget(
        sm, Fact(id="f1", proposition="a normal fact", topic="t"), budget_s=8.0,
    )
    assert res.get("deferred") is False
    # the fact is actually persisted (not just accepted)
    assert sm.get("f1") is not None


def test_store_within_budget_deferred_write_eventually_lands(tmp_path):
    """Deferred ≠ lost: once the lock frees, the background thread completes."""
    from engram.semantic import store_within_budget

    db = tmp_path / "sem.db"
    sm = SemanticMemory(db_path=db)
    sm.store(Fact(id="seed", proposition="seed fact", topic="t"))

    started, release = threading.Event(), threading.Event()
    holder = threading.Thread(
        target=_hold_write_lock, args=(db, 30.0, started, release), daemon=True,
    )
    holder.start()
    assert started.wait(timeout=5)

    res = store_within_budget(
        sm, Fact(id="late", proposition="late fact", topic="t"), budget_s=1.0,
    )
    assert res.get("deferred") is True
    release.set()
    holder.join(timeout=5)

    # the background write completes once the lock frees
    deadline = time.time() + 10
    while time.time() < deadline and sm.get("late") is None:
        time.sleep(0.2)
    assert sm.get("late") is not None, "deferred write was lost — must eventually land"
