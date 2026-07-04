"""FORGIA pezzo #163 — SleepEngine `_stage_bundle_discovery`.

Discovers natural skill bundles (skill-pairs that frequently co-occur)
and exposes them on the SleepReport for downstream stages and
audit. Does NOT yet emit compound-macro skills — that's pezzo #164+.
"""
from __future__ import annotations

import time
from pathlib import Path

from engram.episode import Episode, Trace
from engram.memory import EpisodicMemory
from engram.semantic import SemanticMemory
from engram.skill import SkillLibrary
from engram.sleep import SleepEngine, SleepReport


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


def test_sleep_report_has_bundle_fields():
    """The SleepReport must declare bundle-discovery fields up-front."""
    r = SleepReport()
    assert hasattr(r, "n_bundles_proposed")
    assert hasattr(r, "bundle_candidates")
    assert r.n_bundles_proposed == 0
    assert r.bundle_candidates == []


def test_stage_bundle_discovery_populates_report(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("HIPPO_OFFLINE", "1")
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    skills = SkillLibrary(
        dir_path=tmp_path / "sk", db_path=tmp_path / "sk" / "idx.db",
    )
    sem = SemanticMemory(db_path=tmp_path / "sem.db")
    # Strong A∩C bundle (5×), weaker A∩B bundle (3×).
    for i in range(5):
        mem.store(_ep(f"ac{i}", skills=["A", "C"]))
    for i in range(3):
        mem.store(_ep(f"ab{i}", skills=["A", "B"]))
    eng = SleepEngine(memory=mem, skills=skills, semantic=sem)
    report = SleepReport()
    eng._stage_bundle_discovery(report, min_count=3, min_overlap=0.5)
    # Both bundles pass count>=3 and overlap=1.0
    assert report.n_bundles_proposed == 2
    pairs = {(a, b) for (a, b, _) in report.bundle_candidates}
    assert pairs == {("A", "C"), ("A", "B")}


def test_stage_bundle_discovery_empty_memory(tmp_path: Path):
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    skills = SkillLibrary(
        dir_path=tmp_path / "sk", db_path=tmp_path / "sk" / "idx.db",
    )
    sem = SemanticMemory(db_path=tmp_path / "sem.db")
    eng = SleepEngine(memory=mem, skills=skills, semantic=sem)
    report = SleepReport()
    eng._stage_bundle_discovery(report)
    assert report.n_bundles_proposed == 0
    assert report.bundle_candidates == []
