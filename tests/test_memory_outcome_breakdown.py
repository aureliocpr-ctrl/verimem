"""FORGIA pezzo #143 — `EpisodicMemory.outcome_breakdown()`."""
from __future__ import annotations

import time
from pathlib import Path

from engram.episode import Episode, Trace
from engram.memory import EpisodicMemory


def _ep(eid: str, outcome: str) -> Episode:
    return Episode(
        id=eid, task_id=eid, task_text=eid,
        outcome=outcome,  # type: ignore[arg-type]
        final_answer="ok",
        traces=[Trace(step=1, thought="t", action="a",
                      action_input="", observation="o")],
        tokens_used=1, skills_used=[],
        created_at=time.time(),
    )


def test_outcome_breakdown_empty(tmp_path: Path):
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    assert mem.outcome_breakdown() == {}


def test_outcome_breakdown_aggregates(tmp_path: Path):
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    for i in range(3):
        mem.store(_ep(f"s{i}", "success"))
    for i in range(2):
        mem.store(_ep(f"f{i}", "failure"))
    b = mem.outcome_breakdown()
    assert b["success"] == 3
    assert b["failure"] == 2
    assert sum(b.values()) == 5
