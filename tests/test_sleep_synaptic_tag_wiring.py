"""FORGIA pezzo #176 — wire `_stage_synaptic_tagging` into `cycle()`."""
from __future__ import annotations

import dataclasses
from pathlib import Path

from verimem import config as config_mod
from verimem.config import CONFIG
from verimem.episode import Episode, Trace
from verimem.memory import EpisodicMemory
from verimem.semantic import SemanticMemory
from verimem.skill import SkillLibrary
from verimem.sleep import SleepEngine


def _patch_config(monkeypatch, **fields) -> None:
    new = dataclasses.replace(CONFIG, **fields)
    monkeypatch.setattr(config_mod, "CONFIG", new)
    from verimem import memory as memory_mod
    from verimem import sleep as sleep_mod
    monkeypatch.setattr(sleep_mod, "CONFIG", new)
    monkeypatch.setattr(memory_mod, "CONFIG", new)


def _ep(eid, *, skills, outcome, ts) -> Episode:
    return Episode(
        id=eid, task_id=eid, task_text=eid,
        outcome=outcome,  # type: ignore[arg-type]
        final_answer="ok",
        traces=[Trace(step=1, thought="t", action="a",
                      action_input="", observation="o")],
        tokens_used=1, skills_used=list(skills),
        created_at=ts,
    )


def _build(tmp_path: Path) -> SleepEngine:
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    skills = SkillLibrary(
        dir_path=tmp_path / "sk", db_path=tmp_path / "sk" / "idx.db",
    )
    sem = SemanticMemory(db_path=tmp_path / "sem.db")
    return SleepEngine(memory=mem, skills=skills, semantic=sem)


def test_cycle_skips_synaptic_tag_by_default(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("HIPPO_OFFLINE", "1")
    eng = _build(tmp_path)
    import time as _t
    now = _t.time()
    eng.memory.store(_ep("f1", skills=["A"], outcome="failure", ts=now))
    eng.memory.store(_ep("s1", skills=["A"], outcome="success", ts=now + 60))
    eng.memory.update_salience("f1", 0.30)
    report = eng.cycle()
    assert report.n_synaptic_tags == 0
    refreshed = eng.memory.get("f1")
    assert abs(refreshed.salience_score - 0.30) < 1e-6


def test_cycle_runs_synaptic_tagging_when_enabled(
    tmp_path: Path, monkeypatch,
):
    monkeypatch.setenv("HIPPO_OFFLINE", "1")
    _patch_config(
        monkeypatch,
        synaptic_tagging_enabled=True,
        synaptic_tag_window_s=120.0,
        synaptic_tag_salience_boost=0.25,
    )
    eng = _build(tmp_path)
    import time as _t
    now = _t.time()
    eng.memory.store(_ep("f1", skills=["A"], outcome="failure", ts=now))
    eng.memory.store(_ep("s1", skills=["A"], outcome="success", ts=now + 60))
    eng.memory.update_salience("f1", 0.30)
    report = eng.cycle()
    assert report.n_synaptic_tags == 1
    refreshed = eng.memory.get("f1")
    assert abs(refreshed.salience_score - 0.55) < 1e-6
