"""FORGIA pezzo #167 — `WakeAgent.compound_skills()`.

Returns the list of skills that are *compound* — i.e. were
synthesized from a bundle of two or more parent skills. Useful for
dashboards to surface what HippoAgent learned to abstract.
"""
from __future__ import annotations

from pathlib import Path

from verimem.memory import EpisodicMemory
from verimem.skill import Skill, SkillLibrary
from verimem.wake import WakeAgent


def test_compound_skills_empty(tmp_path: Path):
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    skills = SkillLibrary(
        dir_path=tmp_path / "sk", db_path=tmp_path / "sk" / "idx.db",
    )
    wake = WakeAgent(memory=mem, skills=skills)
    assert wake.compound_skills() == []


def test_compound_skills_filters_by_parent_skills(tmp_path: Path):
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    skills = SkillLibrary(
        dir_path=tmp_path / "sk", db_path=tmp_path / "sk" / "idx.db",
    )
    skills.store(Skill(id="s1", name="leaf1", trigger="t", body="b"))
    skills.store(Skill(id="s2", name="leaf2", trigger="t", body="b"))
    skills.store(
        Skill(id="m1", name="leaf1_then_leaf2", trigger="t",
              body="b", parent_skills=["s1", "s2"]),
    )
    wake = WakeAgent(memory=mem, skills=skills)
    out = wake.compound_skills()
    assert len(out) == 1
    assert out[0].id == "m1"
    assert out[0].parent_skills == ["s1", "s2"]


def test_compound_skills_excludes_single_parent(tmp_path: Path):
    """A skill with only ONE parent is a refinement, not a compound."""
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    skills = SkillLibrary(
        dir_path=tmp_path / "sk", db_path=tmp_path / "sk" / "idx.db",
    )
    skills.store(Skill(id="parent", name="p", trigger="t", body="b"))
    skills.store(
        Skill(id="refined", name="p_v2", trigger="t", body="b",
              parent_skills=["parent"]),
    )
    wake = WakeAgent(memory=mem, skills=skills)
    assert wake.compound_skills() == []
