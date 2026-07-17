"""FORGIA pezzo #92 — `EpisodicMemory.count(outcome_filter=...)`."""
from __future__ import annotations

import time
from pathlib import Path

from verimem.episode import Episode, Trace
from verimem.memory import EpisodicMemory


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


def test_count_no_filter(tmp_path: Path):
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    for i in range(3):
        mem.store(_ep(f"e{i}", outcome="success"))
    mem.store(_ep("ef", outcome="failure"))
    assert mem.count() == 4


def test_count_outcome_filter(tmp_path: Path):
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    for i in range(5):
        mem.store(_ep(f"s{i}", outcome="success"))
    for i in range(2):
        mem.store(_ep(f"f{i}", outcome="failure"))
    assert mem.count() == 7
    assert mem.count(outcome_filter="success") == 5
    assert mem.count(outcome_filter="failure") == 2
    # invalid filter falls back to no-filter (defensive).
    assert mem.count(outcome_filter="garbage") == 7
