"""Audit#2 2026-06-08 A-7: EpisodicMemory.decay_prune did a hard
`DELETE FROM episodes` with NO undo trail — facts have facts_undo_log +
restore, but episode decay (which runs automatically every sleep cycle) was
irreversible, so a buggy/too-aggressive decay destroyed episodes permanently.
Fix: archive each pruned episode (+ traces) to a bounded episodes_undo_log
before the delete, and add restore_decayed() to reverse a bad prune.
"""
from __future__ import annotations

import time

from verimem.episode import Episode
from verimem.memory import EpisodicMemory


def test_decay_prune_is_reversible_via_undo_log(tmp_path):
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    ancient = time.time() - 10**9  # ~31y ago → retention ≈ 0 → decays out
    ep = Episode(
        task_id="t", task_text="a recoverable decayed task",
        final_answer="ans", outcome="success", created_at=ancient,
    )
    mem.store(ep)
    assert mem.get(ep.id) is not None

    pruned = mem.decay_prune(retention_threshold=0.30)
    assert ep.id in pruned, f"expected the ancient episode to decay; got {pruned}"
    assert mem.get(ep.id) is None  # hard-deleted

    restored = mem.restore_decayed()
    assert restored >= 1
    back = mem.get(ep.id)
    assert back is not None, "decay prune was irreversible (A-7)"
    assert back.task_text == "a recoverable decayed task"


def test_undo_log_is_bounded(tmp_path, monkeypatch):
    # The undo trail must not grow without bound (it would defeat decay's
    # purpose of bounding episodes.db). Cap is enforced on write.
    import verimem.memory as memmod
    monkeypatch.setattr(memmod, "_EPISODES_UNDO_CAP", 3)
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    ancient = time.time() - 10**9
    for i in range(6):
        mem.store(Episode(
            task_id="t", task_text=f"decayed-{i}", final_answer="a",
            outcome="success", created_at=ancient,
        ))
    mem.decay_prune(retention_threshold=0.30)
    with mem._connect() as conn:
        n = conn.execute("SELECT COUNT(*) FROM episodes_undo_log").fetchone()[0]
    assert n <= 3, f"undo log unbounded: {n} rows kept with cap=3"
