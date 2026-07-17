"""FORGIA pezzo #170 — `_stage_negative_bundles`: lateral inhibition tagging.

For each pair (a,b,count,fail_ratio) returned by
`memory.negative_bundle_candidates`, mark `a.antagonists.append(b)`
and `b.antagonists.append(a)`. Skips when either skill is missing
or the antagonist already registered (idempotent).
"""
from __future__ import annotations

import time
from pathlib import Path

from verimem.episode import Episode, Trace
from verimem.memory import EpisodicMemory
from verimem.semantic import SemanticMemory
from verimem.skill import Skill, SkillLibrary
from verimem.sleep import SleepEngine, SleepReport


def _ep(eid: str, *, skills: list[str], outcome: str) -> Episode:
    return Episode(
        id=eid, task_id=eid, task_text=eid,
        outcome=outcome,  # type: ignore[arg-type]
        final_answer="ok",
        traces=[Trace(step=1, thought="t", action="a",
                      action_input="", observation="o")],
        tokens_used=1, skills_used=list(skills),
        created_at=time.time(),
    )


def _build(tmp_path: Path) -> SleepEngine:
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    skills = SkillLibrary(
        dir_path=tmp_path / "sk", db_path=tmp_path / "sk" / "idx.db",
    )
    sem = SemanticMemory(db_path=tmp_path / "sem.db")
    return SleepEngine(memory=mem, skills=skills, semantic=sem)


def test_negative_bundle_stage_no_failures(tmp_path: Path):
    eng = _build(tmp_path)
    eng.skills.store(Skill(id="A", name="a", trigger="t", body="b"))
    eng.skills.store(Skill(id="B", name="b", trigger="t", body="b"))
    for i in range(5):
        eng.memory.store(_ep(f"s{i}", skills=["A", "B"], outcome="success"))
    report = SleepReport()
    eng._stage_negative_bundles(report)
    assert report.n_antagonisms == 0
    assert eng.skills.get("A").antagonists == []
    assert eng.skills.get("B").antagonists == []


def test_negative_bundle_stage_marks_pair(tmp_path: Path):
    eng = _build(tmp_path)
    eng.skills.store(Skill(id="A", name="a", trigger="t", body="b"))
    eng.skills.store(Skill(id="B", name="b", trigger="t", body="b"))
    for i in range(5):
        eng.memory.store(_ep(f"f{i}", skills=["A", "B"], outcome="failure"))
    report = SleepReport()
    eng._stage_negative_bundles(report, min_count=3, min_fail_ratio=0.7)
    assert report.n_antagonisms == 1
    a = eng.skills.get("A")
    b = eng.skills.get("B")
    assert "B" in a.antagonists
    assert "A" in b.antagonists


def test_negative_bundle_stage_idempotent(tmp_path: Path):
    """Running the stage twice doesn't duplicate antagonist entries."""
    eng = _build(tmp_path)
    eng.skills.store(Skill(id="A", name="a", trigger="t", body="b"))
    eng.skills.store(Skill(id="B", name="b", trigger="t", body="b"))
    for i in range(5):
        eng.memory.store(_ep(f"f{i}", skills=["A", "B"], outcome="failure"))
    report1 = SleepReport()
    eng._stage_negative_bundles(report1, min_count=3, min_fail_ratio=0.7)
    report2 = SleepReport()
    eng._stage_negative_bundles(report2, min_count=3, min_fail_ratio=0.7)
    assert eng.skills.get("A").antagonists.count("B") == 1
    assert eng.skills.get("B").antagonists.count("A") == 1


def test_negative_bundle_stage_skips_missing(tmp_path: Path):
    eng = _build(tmp_path)
    # Only A exists; B has been retired/deleted but still in episodes.
    eng.skills.store(Skill(id="A", name="a", trigger="t", body="b"))
    for i in range(5):
        eng.memory.store(_ep(f"f{i}", skills=["A", "B"], outcome="failure"))
    report = SleepReport()
    eng._stage_negative_bundles(report, min_count=3, min_fail_ratio=0.7)
    # Stage runs without crash; A keeps no antagonist of a missing skill.
    assert eng.skills.get("A").antagonists == []
    assert report.n_antagonisms == 0
