"""FORGIA pezzo #161 — `WakeAgent.skill_bundle_candidates` thin alias."""
from __future__ import annotations

import time
from pathlib import Path

from engram.episode import Episode, Trace
from engram.memory import EpisodicMemory
from engram.skill import SkillLibrary
from engram.wake import WakeAgent


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


def test_wake_skill_bundle_candidates_aliases_memory(tmp_path: Path):
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    skills = SkillLibrary(
        dir_path=tmp_path / "sk", db_path=tmp_path / "sk" / "idx.db",
    )
    for i in range(3):
        mem.store(_ep(f"ab{i}", skills=["A", "B"]))
    wake = WakeAgent(memory=mem, skills=skills)
    res = wake.skill_bundle_candidates(min_count=2, min_overlap=0.5)
    assert res == [("A", "B", 3)]
    assert wake.skill_bundle_candidates(min_count=10) == []
