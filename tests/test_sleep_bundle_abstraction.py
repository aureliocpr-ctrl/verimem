"""FORGIA pezzo #165 — `_stage_abstract_bundles`: bundle → candidate skill.

Pure-mechanical (no LLM): for each bundle (a,b,count) in
`report.bundle_candidates`, compose a candidate skill named
``a_then_b`` whose body concatenates a.body and b.body, with both
parents pointed to in `parent_skills`. The skill is stored as
`status="candidate"` so it goes through the standard fitness/trial
pipeline before promotion.
"""
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
from verimem.sleep import SleepEngine, SleepReport


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
    return SleepEngine(memory=mem, skills=skills, semantic=sem)


def test_abstract_bundles_empty_report(tmp_path: Path):
    eng = _build(tmp_path)
    report = SleepReport()
    eng._stage_abstract_bundles(report)
    assert [s for s in eng.skills.all() if s.parent_skills] == []


def test_abstract_bundles_creates_candidate_with_parents(tmp_path: Path):
    eng = _build(tmp_path)
    sa = Skill(id="a", name="parse", trigger="parse csv",
               body="step 1: read file", status="promoted")
    sb = Skill(id="b", name="validate", trigger="validate schema",
               body="step 2: check schema", status="promoted")
    eng.skills.store(sa)
    eng.skills.store(sb)
    report = SleepReport()
    report.bundle_candidates = [("a", "b", 5)]
    eng._stage_abstract_bundles(report)
    new_skills = [s for s in eng.skills.all() if s.parent_skills]
    assert len(new_skills) == 1
    macro = new_skills[0]
    assert macro.parent_skills == ["a", "b"]
    assert macro.status == "candidate"
    assert "step 1" in macro.body
    assert "step 2" in macro.body
    # name follows convention
    assert macro.name == "parse_then_validate"


def test_abstract_bundles_skips_when_either_skill_missing(tmp_path: Path):
    eng = _build(tmp_path)
    sa = Skill(id="a", name="alpha", trigger="t1", body="bA",
               status="promoted")
    eng.skills.store(sa)
    # b is referenced in bundle but doesn't exist in library
    report = SleepReport()
    report.bundle_candidates = [("a", "b", 5)]
    eng._stage_abstract_bundles(report)
    assert [s for s in eng.skills.all() if s.parent_skills] == []


def test_abstract_bundles_skips_when_macro_already_exists(tmp_path: Path):
    eng = _build(tmp_path)
    sa = Skill(id="a", name="alpha", trigger="t1", body="bA",
               status="promoted")
    sb = Skill(id="b", name="beta", trigger="t2", body="bB",
               status="promoted")
    eng.skills.store(sa)
    eng.skills.store(sb)
    # Pre-existing macro with the same parent set
    pre = Skill(id="m1", name="alpha_then_beta", trigger="t1+t2",
                body="bA\nbB", status="candidate", parent_skills=["a", "b"])
    eng.skills.store(pre)
    report = SleepReport()
    report.bundle_candidates = [("a", "b", 5)]
    eng._stage_abstract_bundles(report)
    # No duplicate created; same skill_id
    macros = [s for s in eng.skills.all() if s.parent_skills == ["a", "b"]]
    assert len(macros) == 1
    assert macros[0].id == "m1"


def test_abstract_bundles_records_skill_count_on_report(tmp_path: Path):
    eng = _build(tmp_path)
    sa = Skill(id="a", name="alpha", trigger="t1", body="bA",
               status="promoted")
    sb = Skill(id="b", name="beta", trigger="t2", body="bB",
               status="promoted")
    eng.skills.store(sa)
    eng.skills.store(sb)
    report = SleepReport()
    report.bundle_candidates = [("a", "b", 5)]
    eng._stage_abstract_bundles(report)
    assert report.n_bundle_skills == 1
