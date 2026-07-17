"""FORGIA pezzo #139 — `EpisodicMemory.skill_usage_histogram()`."""
from __future__ import annotations

import time
from pathlib import Path

from verimem.episode import Episode, Trace
from verimem.memory import EpisodicMemory


def _ep(eid: str, skills: list[str]) -> Episode:
    return Episode(
        id=eid, task_id=eid, task_text=eid,
        outcome="success", final_answer="ok",
        traces=[Trace(step=1, thought="t", action="a",
                      action_input="", observation="o")],
        tokens_used=1, skills_used=list(skills),
        created_at=time.time(),
    )


def test_skill_histogram_empty(tmp_path: Path):
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    assert mem.skill_usage_histogram() == {}


def test_skill_histogram_counts(tmp_path: Path):
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    mem.store(_ep("e1", ["A", "B"]))
    mem.store(_ep("e2", ["A"]))
    mem.store(_ep("e3", ["B", "C"]))
    h = mem.skill_usage_histogram()
    assert h == {"A": 2, "B": 2, "C": 1}


def test_skill_histogram_ignores_episodes_without_skills(tmp_path: Path):
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    mem.store(_ep("e1", []))
    mem.store(_ep("e2", ["A"]))
    h = mem.skill_usage_histogram()
    assert h == {"A": 1}
