"""FORGIA pezzo #159 — `WakeAgent.skill_co_occurrence` thin alias."""
from __future__ import annotations

import time
from pathlib import Path

from verimem.episode import Episode, Trace
from verimem.memory import EpisodicMemory
from verimem.skill import SkillLibrary
from verimem.wake import WakeAgent


def _ep(eid: str, *, skills: list[str]) -> Episode:
    return Episode(
        id=eid, task_id=eid, task_text=eid,
        outcome="success",
        final_answer="ok",
        traces=[Trace(step=1, thought="t", action="a",
                      action_input="", observation="o")],
        tokens_used=1, skills_used=list(skills),
        created_at=time.time(),
    )


def test_wake_skill_co_occurrence_aliases_memory(tmp_path: Path):
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    skills = SkillLibrary(
        dir_path=tmp_path / "sk", db_path=tmp_path / "sk" / "idx.db",
    )
    mem.store(_ep("e1", skills=["A", "B"]))
    mem.store(_ep("e2", skills=["A", "B"]))
    mem.store(_ep("e3", skills=["A", "C"]))
    wake = WakeAgent(memory=mem, skills=skills)
    assert wake.skill_co_occurrence("A") == {"B": 2, "C": 1}
    assert wake.skill_co_occurrence("A", top_k=1) == {"B": 2}
    assert wake.skill_co_occurrence("UNKNOWN") == {}
