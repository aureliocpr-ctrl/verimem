"""FORGIA pezzo #172 — wire `_stage_negative_bundles` into `cycle()`."""
from __future__ import annotations

import dataclasses
import time
from pathlib import Path

from verimem import config as config_mod
from verimem.config import CONFIG
from verimem.episode import Episode, Trace
from verimem.memory import EpisodicMemory
from verimem.semantic import SemanticMemory
from verimem.skill import Skill, SkillLibrary
from verimem.sleep import SleepEngine


def _patch_config(monkeypatch, **fields) -> None:
    new = dataclasses.replace(CONFIG, **fields)
    monkeypatch.setattr(config_mod, "CONFIG", new)
    from verimem import memory as memory_mod
    from verimem import sleep as sleep_mod
    monkeypatch.setattr(sleep_mod, "CONFIG", new)
    monkeypatch.setattr(memory_mod, "CONFIG", new)


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


def test_cycle_skips_negative_bundle_by_default(tmp_path: Path, monkeypatch):
    """Default config: negative-bundle stage does NOT fire."""
    monkeypatch.setenv("HIPPO_OFFLINE", "1")
    eng = _build(tmp_path)
    eng.skills.store(Skill(id="A", name="a", trigger="t", body="b"))
    eng.skills.store(Skill(id="B", name="b", trigger="t", body="b"))
    for i in range(5):
        eng.memory.store(_ep(f"f{i}", skills=["A", "B"], outcome="failure"))
    report = eng.cycle()
    assert report.n_antagonisms == 0
    assert eng.skills.get("A").antagonists == []


def test_cycle_runs_negative_bundle_when_enabled(
    tmp_path: Path, monkeypatch,
):
    monkeypatch.setenv("HIPPO_OFFLINE", "1")
    _patch_config(
        monkeypatch,
        negative_bundle_enabled=True,
        negative_bundle_min_count=3,
        negative_bundle_min_fail_ratio=0.7,
    )
    eng = _build(tmp_path)
    eng.skills.store(Skill(id="A", name="a", trigger="t", body="b"))
    eng.skills.store(Skill(id="B", name="b", trigger="t", body="b"))
    for i in range(5):
        eng.memory.store(_ep(f"f{i}", skills=["A", "B"], outcome="failure"))
    report = eng.cycle()
    assert report.n_antagonisms == 1
    assert "B" in eng.skills.get("A").antagonists
    assert "A" in eng.skills.get("B").antagonists
