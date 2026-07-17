"""The EPISODE save path must NEVER block the caller on a slow embedding.

Twin of the fact-store hang (test_save_encode_circuit_breaker.py). The fact
path was fixed 2026-06-06; the episode path (`EpisodicMemory.store`) still did a
raw `embedding.encode(episode.summary())` with NO budget — plus two more encodes
inside `compute_salience` (`_raw_cosine_recall` + neighbour/summary encodes). A
starved/hung daemon (alive but slow under heavy concurrent load — the exact
40-min save-hang Aurelio hit) would wedge `hippo_record_episode` for MINUTES.

Fix: `store(embed="auto")` resolves to a *budgeted* sync when the encode daemon
looks warm, else DEFERS. On budget-overrun OR cold daemon the episode is written
with an empty-embedding sentinel (length-0 blob, NULL dg) — instant, keyword-
findable, recallable-by-cosine once `backfill_pending_embeddings` heals it.
Explicit `embed="sync"` stays byte-identical (legacy/tests rely on it).
"""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path

import numpy as np
import pytest

import verimem.memory as mem
from verimem import encode_service as es
from verimem.config import CONFIG
from verimem.episode import Episode


def _make_ep(text: str = "circuit-breaker episode") -> Episode:
    return Episode(
        task_id="t1",
        task_text=text,
        final_answer="done",
        outcome="success",
    )


def _summary_blob_len(db_path: Path, ep_id: str) -> int | None:
    """Raw byte length of the stored summary_embedding (0 == deferred sentinel)."""
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT length(summary_embedding) AS n, dg_embedding "
            "FROM episodes WHERE id = ?",
            (ep_id,),
        ).fetchone()
    finally:
        conn.close()
    return None if row is None else row[0]


def _dg_is_null(db_path: Path, ep_id: str) -> bool:
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT dg_embedding FROM episodes WHERE id = ?", (ep_id,)
        ).fetchone()
    finally:
        conn.close()
    return row is not None and row[0] is None


def test_store_auto_defers_under_slow_encode_no_hang(monkeypatch, tmp_path):
    """Daemon LOOKS usable (answers the warmth ping) but the encode is
    pathologically slow → store(embed='auto') must DEFER, never hang."""
    monkeypatch.setattr(es, "daemon_usable", lambda: True)  # warm -> budgeted sync
    monkeypatch.setattr(mem, "_SAVE_ENCODE_BUDGET_S", 0.4)

    def _slow(*_a, **_k):
        time.sleep(10)
        return np.ones(CONFIG.embedding_dim, dtype=np.float32)

    monkeypatch.setattr(mem.embedding, "encode", _slow)

    db = tmp_path / "ep.db"
    m = mem.EpisodicMemory(db_path=db)
    ep = _make_ep()

    t0 = time.time()
    m.store(ep, embed="auto")
    elapsed = time.time() - t0

    assert elapsed < 3.0, f"episode store(embed='auto') hung {elapsed:.1f}s"
    assert m.get(ep.id) is not None, "episode must persist despite deferred embedding"
    assert _summary_blob_len(db, ep.id) == 0, "deferred episode must store empty sentinel"
    assert _dg_is_null(db, ep.id), "deferred episode must store NULL dg_embedding"


def test_store_auto_defers_when_daemon_cold_no_encode(monkeypatch, tmp_path):
    """Cold/unusable daemon → DEFER instantly WITHOUT ever calling encode
    (no in-process ~22s cold-load on the hot path)."""
    monkeypatch.setattr(es, "daemon_usable", lambda: False)

    def _boom_if_called(*_a, **_k):
        raise AssertionError("encode must NOT be called when daemon is cold")

    monkeypatch.setattr(mem.embedding, "encode", _boom_if_called)

    db = tmp_path / "ep.db"
    m = mem.EpisodicMemory(db_path=db)
    ep = _make_ep()

    t0 = time.time()
    m.store(ep, embed="auto")
    elapsed = time.time() - t0

    assert elapsed < 3.0
    assert m.get(ep.id) is not None
    assert _summary_blob_len(db, ep.id) == 0


def test_store_sync_encodes_and_persists_vector(monkeypatch, tmp_path):
    """Explicit embed='sync' (the default) keeps the legacy path: it embeds
    NOW and persists a real vector + dg blob — byte-compatible behaviour."""
    monkeypatch.setattr(
        mem.embedding, "encode",
        lambda *_a, **_k: np.ones(CONFIG.embedding_dim, dtype=np.float32),
    )

    db = tmp_path / "ep.db"
    m = mem.EpisodicMemory(db_path=db)
    ep = _make_ep()

    m.store(ep)  # default embed="sync"

    assert m.get(ep.id) is not None
    assert _summary_blob_len(db, ep.id) > 0, "sync store must persist a real embedding"
    assert not _dg_is_null(db, ep.id), "sync store must persist a dg_embedding"


def test_backfill_heals_deferred_episode(monkeypatch, tmp_path):
    """The async other half: a deferred episode (empty sentinel) is healed by
    backfill_pending_embeddings → real summary_embedding + dg filled in."""
    # 1) Defer it (cold daemon).
    monkeypatch.setattr(es, "daemon_usable", lambda: False)
    db = tmp_path / "ep.db"
    m = mem.EpisodicMemory(db_path=db)
    ep = _make_ep()
    m.store(ep, embed="auto")
    assert _summary_blob_len(db, ep.id) == 0, "precondition: episode is deferred"

    # 2) Heal it (daemon warm now → real encode).
    monkeypatch.setattr(
        mem.embedding, "encode",
        lambda *_a, **_k: np.ones(CONFIG.embedding_dim, dtype=np.float32),
    )
    n = m.backfill_pending_embeddings()

    assert n == 1, f"backfill must heal exactly 1 deferred episode, healed {n}"
    assert _summary_blob_len(db, ep.id) > 0, "summary_embedding must be filled after backfill"
    assert not _dg_is_null(db, ep.id), "dg_embedding must be filled after backfill"


def test_dg_backfill_skips_deferred_episode_no_crash(monkeypatch, tmp_path):
    """REGRESSION: a deferred episode has summary_embedding=b'' AND
    dg_embedding=NULL. `_backfill_dg_embeddings` selects `WHERE dg_embedding IS
    NULL` and `deserialize(summary)+dg_encode(...)` — on the empty sentinel that
    would dg_encode a shape-(0,) array and CRASH, taking down dg-recall for the
    WHOLE corpus. It must SKIP deferred rows (dg stays NULL until the summary is
    healed by backfill_pending_embeddings)."""
    monkeypatch.setattr(es, "daemon_usable", lambda: False)
    db = tmp_path / "ep.db"
    m = mem.EpisodicMemory(db_path=db)
    ep = _make_ep()
    m.store(ep, embed="auto")  # deferred: summary empty, dg NULL
    assert _summary_blob_len(db, ep.id) == 0

    # Must not raise (was: dg_encode on an empty (0,) array → ValueError).
    n = m._backfill_dg_embeddings()

    assert _dg_is_null(db, ep.id), "deferred episode dg must stay NULL until summary heals"
    assert n == 0, "no real (summary-bearing) NULL-dg rows → nothing to backfill"
