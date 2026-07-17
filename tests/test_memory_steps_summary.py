"""FORGIA pezzo #144 — `EpisodicMemory.steps_summary()`."""
from __future__ import annotations

import time
from pathlib import Path

from verimem.episode import Episode, Trace
from verimem.memory import EpisodicMemory


def _ep(eid: str, n_steps: int) -> Episode:
    return Episode(
        id=eid, task_id=eid, task_text=eid,
        outcome="success", final_answer="ok",
        traces=[
            Trace(step=i, thought="t", action="a",
                  action_input="", observation="o")
            for i in range(1, n_steps + 1)
        ],
        tokens_used=1, skills_used=[],
        created_at=time.time(),
    )


def test_steps_summary_empty(tmp_path: Path):
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    s = mem.steps_summary()
    assert s["n"] == 0.0
    assert s["max"] == 0.0


def test_steps_summary_aggregates(tmp_path: Path):
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    mem.store(_ep("e1", 1))
    mem.store(_ep("e2", 3))
    mem.store(_ep("e3", 5))
    s = mem.steps_summary()
    assert s["n"] == 3.0
    assert s["min"] == 1.0
    assert s["max"] == 5.0
    assert s["mean"] == 3.0
