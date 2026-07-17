"""FORGIA pezzo #158 — `EpisodicMemory.skill_co_occurrence(skill_id, top_k)`.

Returns a dict mapping {other_skill_id: co_occurrence_count} for skills
that appeared together with `skill_id` in the same episode. Useful for
discovering natural skill bundles that the sleep engine may want to
abstract into a single compound macro.
"""
from __future__ import annotations

import time
from pathlib import Path

from verimem.episode import Episode, Trace
from verimem.memory import EpisodicMemory


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


def test_skill_co_occurrence_unknown(tmp_path: Path):
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    mem.store(_ep("e1", skills=["A", "B"]))
    assert mem.skill_co_occurrence("UNKNOWN") == {}


def test_skill_co_occurrence_excludes_self(tmp_path: Path):
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    mem.store(_ep("e1", skills=["A", "A", "B"]))  # dup A in same ep
    assert "A" not in mem.skill_co_occurrence("A")


def test_skill_co_occurrence_counts(tmp_path: Path):
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    mem.store(_ep("e1", skills=["A", "B", "C"]))
    mem.store(_ep("e2", skills=["A", "B"]))
    mem.store(_ep("e3", skills=["A", "C"]))
    mem.store(_ep("e4", skills=["B", "C"]))  # no A here
    co = mem.skill_co_occurrence("A")
    assert co == {"B": 2, "C": 2}


def test_skill_co_occurrence_top_k(tmp_path: Path):
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    mem.store(_ep("e1", skills=["A", "B"]))
    mem.store(_ep("e2", skills=["A", "B"]))
    mem.store(_ep("e3", skills=["A", "B"]))
    mem.store(_ep("e4", skills=["A", "C"]))
    mem.store(_ep("e5", skills=["A", "D"]))
    co = mem.skill_co_occurrence("A", top_k=2)
    assert len(co) == 2
    assert "B" in co  # most frequent must be present
    assert co["B"] == 3
