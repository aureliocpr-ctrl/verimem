"""FORGIA pezzo #179 — wire `_stage_crossover` into `cycle()`."""
from __future__ import annotations

import dataclasses
from pathlib import Path

from verimem import config as config_mod
from verimem.config import CONFIG
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


def _build(tmp_path: Path) -> SleepEngine:
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    skills = SkillLibrary(
        dir_path=tmp_path / "sk", db_path=tmp_path / "sk" / "idx.db",
    )
    sem = SemanticMemory(db_path=tmp_path / "sem.db")
    return SleepEngine(memory=mem, skills=skills, semantic=sem, seed=42)


def _seed_skills(eng: SleepEngine, n: int) -> None:
    for i in range(n):
        eng.skills.store(Skill(
            id=f"S{i}", name=f"sk{i}", trigger=f"t{i}",
            body=f"line{i}_a\nline{i}_b",
            status="promoted", trials=10, successes=9,
        ))


def _seed_episodes(eng: SleepEngine, n: int = 5) -> None:
    """Plant enough episodes so cycle() doesn't bail on sleep_min_episodes."""
    import time as _t

    from verimem.episode import Episode, Trace
    now = _t.time()
    for i in range(n):
        eng.memory.store(Episode(
            id=f"ep{i}", task_id=f"ep{i}", task_text=f"task {i}",
            outcome="success", final_answer="x",
            traces=[Trace(step=1, thought="t", action="a",
                          action_input="", observation="o")],
            tokens_used=1, skills_used=[f"S{i % 3}"],
            created_at=now,
        ))


def test_cycle_no_crossover_by_default(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("HIPPO_OFFLINE", "1")
    eng = _build(tmp_path)
    _seed_skills(eng, 5)
    _seed_episodes(eng, 5)
    report = eng.cycle()
    assert report.n_crossovers == 0
    hybrids = [s for s in eng.skills.all() if "_x_" in s.name]
    assert hybrids == []


def test_cycle_runs_crossover_when_enabled(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("HIPPO_OFFLINE", "1")
    _patch_config(
        monkeypatch,
        crossover_enabled=True,
        crossover_n_pairs=2,
        crossover_top_k=4,
    )
    eng = _build(tmp_path)
    _seed_skills(eng, 5)
    _seed_episodes(eng, 5)
    report = eng.cycle()
    assert report.n_crossovers == 2
    hybrids = [s for s in eng.skills.all() if "_x_" in s.name]
    assert len(hybrids) == 2
