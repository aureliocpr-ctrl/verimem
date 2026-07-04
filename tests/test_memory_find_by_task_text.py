"""FORGIA pezzo #110 — `EpisodicMemory.find_by_task_text(task_text)`."""
from __future__ import annotations

import time
from pathlib import Path

from engram.episode import Episode, Trace
from engram.memory import EpisodicMemory


def _ep(eid: str, text: str) -> Episode:
    return Episode(
        id=eid, task_id=eid, task_text=text,
        outcome="success", final_answer="ok",
        traces=[Trace(step=1, thought="t", action="a",
                      action_input="", observation="o")],
        tokens_used=1, skills_used=[],
        created_at=time.time(),
    )


def test_find_by_task_text_exact_match(tmp_path: Path):
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    mem.store(_ep("e1", "compute factorial of 10"))
    mem.store(_ep("e2", "compute factorial of 10"))
    mem.store(_ep("e3", "send email"))
    out = mem.find_by_task_text("compute factorial of 10")
    assert len(out) == 2
    ids = {e.id for e in out}
    assert ids == {"e1", "e2"}


def test_find_by_task_text_no_match_returns_empty(tmp_path: Path):
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    mem.store(_ep("e1", "task A"))
    out = mem.find_by_task_text("does not exist")
    assert out == []


def test_find_by_task_text_respects_limit(tmp_path: Path):
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    for i in range(5):
        mem.store(_ep(f"e{i}", "same task"))
    out = mem.find_by_task_text("same task", limit=3)
    assert len(out) == 3
