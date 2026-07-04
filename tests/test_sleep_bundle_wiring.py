"""FORGIA pezzo #164 — wire bundle_discovery into consolidate()."""
from __future__ import annotations

import dataclasses
import time
from pathlib import Path

from engram import config as config_mod
from engram.config import CONFIG
from engram.episode import Episode, Trace
from engram.memory import EpisodicMemory
from engram.semantic import SemanticMemory
from engram.skill import SkillLibrary
from engram.sleep import SleepEngine


def _patch_config(monkeypatch, **fields) -> None:
    new = dataclasses.replace(CONFIG, **fields)
    monkeypatch.setattr(config_mod, "CONFIG", new)
    from engram import memory as memory_mod
    from engram import sleep as sleep_mod
    monkeypatch.setattr(sleep_mod, "CONFIG", new)
    monkeypatch.setattr(memory_mod, "CONFIG", new)


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


def _build(tmp_path: Path) -> SleepEngine:
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    skills = SkillLibrary(
        dir_path=tmp_path / "sk", db_path=tmp_path / "sk" / "idx.db",
    )
    sem = SemanticMemory(db_path=tmp_path / "sem.db")
    return SleepEngine(memory=mem, skills=skills, semantic=sem)


def test_consolidate_bundle_disabled_by_default(tmp_path: Path, monkeypatch):
    """Default config: bundle stage does NOT fire even with rich corpus."""
    monkeypatch.setenv("HIPPO_OFFLINE", "1")
    eng = _build(tmp_path)
    for i in range(5):
        eng.memory.store(_ep(f"ac{i}", skills=["A", "C"]))
    # default CONFIG.bundle_discovery_enabled == False
    assert CONFIG.bundle_discovery_enabled is False
    report = eng.cycle()
    assert report.n_bundles_proposed == 0
    assert report.bundle_candidates == []


def test_consolidate_bundle_enabled_populates(
    tmp_path: Path, monkeypatch,
):
    """With flag on, bundle stage runs as part of consolidate()."""
    monkeypatch.setenv("HIPPO_OFFLINE", "1")
    _patch_config(
        monkeypatch,
        bundle_discovery_enabled=True,
        bundle_discovery_min_count=3,
        bundle_discovery_min_overlap=0.5,
    )
    eng = _build(tmp_path)
    for i in range(5):
        eng.memory.store(_ep(f"ac{i}", skills=["A", "C"]))
    for i in range(3):
        eng.memory.store(_ep(f"ab{i}", skills=["A", "B"]))
    report = eng.cycle()
    assert report.n_bundles_proposed == 2
    pairs = {(a, b) for (a, b, _) in report.bundle_candidates}
    assert ("A", "C") in pairs
    assert ("A", "B") in pairs
