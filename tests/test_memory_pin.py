"""FORGIA pezzo #197 — `EpisodicMemory` pin/unpin + decay protection."""
from __future__ import annotations

import time
from pathlib import Path

from verimem.episode import Episode, Trace
from verimem.memory import EpisodicMemory


def _ep(eid: str, *, created_at: float, accessed: float = 0.0,
         access_count: int = 0, salience: float = 0.5) -> Episode:
    return Episode(
        id=eid, task_id=eid, task_text=f"task {eid}",
        outcome="success", final_answer="ok",
        traces=[Trace(step=1, thought="t", action="a",
                       action_input="", observation="o")],
        tokens_used=1, skills_used=[],
        created_at=created_at,
        last_accessed_at=accessed,
        access_count=access_count,
        salience_score=salience,
    )


def test_pin_unpin_roundtrip(tmp_path: Path):
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    mem.store(_ep("e1", created_at=time.time()))
    assert mem.is_pinned("e1") is False
    assert mem.set_pinned("e1", True) is True
    assert mem.is_pinned("e1") is True
    assert mem.set_pinned("e1", False) is True
    assert mem.is_pinned("e1") is False


def test_pin_unknown_returns_false(tmp_path: Path):
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    assert mem.set_pinned("ghost", True) is False
    assert mem.is_pinned("ghost") is False


def test_decay_skips_pinned_episodes(tmp_path: Path):
    """Old episode with low retention is normally decayed; pinned variant stays."""
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    very_old = time.time() - 365 * 24 * 3600  # 1 year ago
    mem.store(_ep("e_old", created_at=very_old))
    mem.store(_ep("e_old_pinned", created_at=very_old))
    mem.set_pinned("e_old_pinned", True)
    candidates = mem.decay_pruning_candidates(retention_threshold=0.99)
    ids = {ep.id for ep in candidates}
    assert "e_old" in ids
    assert "e_old_pinned" not in ids


def test_pinned_episodes_lister(tmp_path: Path):
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    now = time.time()
    mem.store(_ep("a", created_at=now))
    mem.store(_ep("b", created_at=now + 1))
    mem.store(_ep("c", created_at=now + 2))
    mem.set_pinned("a", True)
    mem.set_pinned("c", True)
    pinned = mem.pinned_episodes()
    ids = {ep.id for ep in pinned}
    assert ids == {"a", "c"}
