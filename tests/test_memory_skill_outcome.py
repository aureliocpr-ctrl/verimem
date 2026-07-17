"""FORGIA pezzo #157 — `EpisodicMemory.skill_outcome_breakdown(skill_id)`."""
from __future__ import annotations

import time
from pathlib import Path

from verimem.episode import Episode, Trace
from verimem.memory import EpisodicMemory


def _ep(eid: str, *, skills: list[str], outcome: str = "success") -> Episode:
    return Episode(
        id=eid, task_id=eid, task_text=eid,
        outcome=outcome,  # type: ignore[arg-type]
        final_answer="ok",
        traces=[Trace(step=1, thought="t", action="a",
                      action_input="", observation="o")],
        tokens_used=1, skills_used=list(skills),
        created_at=time.time(),
    )


def test_skill_outcome_breakdown_unknown_skill(tmp_path: Path):
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    mem.store(_ep("e1", skills=["A"]))
    assert mem.skill_outcome_breakdown("UNKNOWN") == {}


def test_skill_outcome_breakdown_aggregates(tmp_path: Path):
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    mem.store(_ep("e1", skills=["A", "B"], outcome="success"))
    mem.store(_ep("e2", skills=["A"], outcome="success"))
    mem.store(_ep("e3", skills=["A"], outcome="failure"))
    mem.store(_ep("e4", skills=["B"], outcome="failure"))
    a = mem.skill_outcome_breakdown("A")
    assert a == {"success": 2, "failure": 1}
    b = mem.skill_outcome_breakdown("B")
    assert b == {"success": 1, "failure": 1}
