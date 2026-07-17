"""FORGIA pezzo #166 — wire _stage_abstract_bundles into cycle()."""
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


def test_cycle_creates_compound_skill_when_bundle_enabled(
    tmp_path: Path, monkeypatch,
):
    monkeypatch.setenv("HIPPO_OFFLINE", "1")
    _patch_config(
        monkeypatch,
        bundle_discovery_enabled=True,
        bundle_discovery_min_count=3,
        bundle_discovery_min_overlap=0.5,
    )
    eng = _build(tmp_path)
    # Pre-store the two parent skills so abstraction has something to
    # combine.
    eng.skills.store(Skill(id="A", name="alpha", trigger="ta",
                            body="bA", status="promoted"))
    eng.skills.store(Skill(id="B", name="beta", trigger="tb",
                            body="bB", status="promoted"))
    # Seed the corpus with bundle co-occurrences A∩B.
    for i in range(5):
        eng.memory.store(_ep(f"ab{i}", skills=["A", "B"]))
    report = eng.cycle()
    assert report.n_bundles_proposed >= 1
    assert report.n_bundle_skills >= 1
    # The compound skill exists in the library.
    macros = [s for s in eng.skills.all() if s.parent_skills == ["A", "B"]]
    assert len(macros) == 1
    assert macros[0].name == "alpha_then_beta"


def test_cycle_no_compound_skill_when_disabled(
    tmp_path: Path, monkeypatch,
):
    monkeypatch.setenv("HIPPO_OFFLINE", "1")
    eng = _build(tmp_path)
    eng.skills.store(Skill(id="A", name="alpha", trigger="ta",
                            body="bA", status="promoted"))
    eng.skills.store(Skill(id="B", name="beta", trigger="tb",
                            body="bB", status="promoted"))
    for i in range(5):
        eng.memory.store(_ep(f"ab{i}", skills=["A", "B"]))
    report = eng.cycle()
    assert report.n_bundle_skills == 0
    assert [s for s in eng.skills.all() if s.parent_skills] == []
