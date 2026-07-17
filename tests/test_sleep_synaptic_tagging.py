"""FORGIA pezzo #175 — `_stage_synaptic_tagging` salience boost."""
from __future__ import annotations

import time
from pathlib import Path

from verimem.episode import Episode, Trace
from verimem.memory import EpisodicMemory
from verimem.semantic import SemanticMemory
from verimem.skill import SkillLibrary
from verimem.sleep import SleepEngine, SleepReport


def _ep(eid: str, *, skills: list[str], outcome: str,
        ts: float, salience: float = 0.5) -> Episode:
    e = Episode(
        id=eid, task_id=eid, task_text=eid,
        outcome=outcome,  # type: ignore[arg-type]
        final_answer="ok",
        traces=[Trace(step=1, thought="t", action="a",
                      action_input="", observation="o")],
        tokens_used=1, skills_used=list(skills),
        created_at=ts,
        salience_score=salience,
    )
    return e


def _build(tmp_path: Path) -> SleepEngine:
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    skills = SkillLibrary(
        dir_path=tmp_path / "sk", db_path=tmp_path / "sk" / "idx.db",
    )
    sem = SemanticMemory(db_path=tmp_path / "sem.db")
    return SleepEngine(memory=mem, skills=skills, semantic=sem)


def test_synaptic_tagging_no_pairs(tmp_path: Path):
    eng = _build(tmp_path)
    eng.memory.store(_ep("s1", skills=["A"], outcome="success", ts=100.0))
    report = SleepReport()
    eng._stage_synaptic_tagging(report, window_s=120.0)
    assert report.n_synaptic_tags == 0


def test_synaptic_tagging_boosts_salience(tmp_path: Path):
    eng = _build(tmp_path)
    eng.memory.store(
        _ep("f1", skills=["A"], outcome="failure", ts=100.0),
    )
    eng.memory.store(
        _ep("s1", skills=["A"], outcome="success", ts=160.0),
    )
    # Force a known baseline salience independent of compute_salience.
    eng.memory.update_salience("f1", 0.30)
    report = SleepReport()
    eng._stage_synaptic_tagging(report, window_s=120.0,
                                 salience_boost=0.25)
    assert report.n_synaptic_tags == 1
    refreshed = eng.memory.get("f1")
    assert refreshed is not None
    # 0.30 + 0.25 = 0.55
    assert abs(refreshed.salience_score - 0.55) < 1e-6


def test_synaptic_tagging_caps_at_one(tmp_path: Path):
    """Boost should never exceed 1.0 even if salience already high."""
    eng = _build(tmp_path)
    eng.memory.store(_ep("f1", skills=["A"], outcome="failure", ts=100.0))
    eng.memory.store(_ep("s1", skills=["A"], outcome="success", ts=110.0))
    eng.memory.update_salience("f1", 0.95)
    report = SleepReport()
    eng._stage_synaptic_tagging(report, window_s=60.0,
                                 salience_boost=0.5)
    refreshed = eng.memory.get("f1")
    assert refreshed.salience_score == 1.0


def test_synaptic_tagging_idempotent_within_cycle(tmp_path: Path):
    """Two failure→success links to the SAME weak episode boost it once."""
    eng = _build(tmp_path)
    eng.memory.store(
        _ep("f1", skills=["A", "B"], outcome="failure", ts=100.0),
    )
    eng.memory.store(_ep("sa", skills=["A"], outcome="success", ts=110.0))
    eng.memory.store(_ep("sb", skills=["B"], outcome="success", ts=130.0))
    eng.memory.update_salience("f1", 0.30)
    report = SleepReport()
    eng._stage_synaptic_tagging(report, window_s=120.0,
                                 salience_boost=0.2)
    # Even if synaptic_tag_candidates returns two pairs for f1,
    # the salience boost is applied at most once per episode.
    refreshed = eng.memory.get("f1")
    assert abs(refreshed.salience_score - 0.5) < 1e-6
    assert report.n_synaptic_tags == 1
