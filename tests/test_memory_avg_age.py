"""FORGIA pezzo #153 — `EpisodicMemory.average_episode_age_s()`."""
from __future__ import annotations

import time
from pathlib import Path

from engram.episode import Episode, Trace
from engram.memory import EpisodicMemory


def _ep(eid: str, ts: float) -> Episode:
    return Episode(
        id=eid, task_id=eid, task_text=eid,
        outcome="success", final_answer="ok",
        traces=[Trace(step=1, thought="t", action="a",
                      action_input="", observation="o")],
        tokens_used=1, skills_used=[],
        created_at=ts,
    )


def test_avg_age_empty(tmp_path: Path):
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    assert mem.average_episode_age_s() == 0.0


def test_avg_age_positive(tmp_path: Path):
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    now = time.time()
    mem.store(_ep("e1", now - 100))
    mem.store(_ep("e2", now - 200))
    mem.store(_ep("e3", now - 300))
    age = mem.average_episode_age_s()
    # mean of (100, 200, 300) ≈ 200, give or take wall-clock drift.
    assert 150.0 < age < 300.0
