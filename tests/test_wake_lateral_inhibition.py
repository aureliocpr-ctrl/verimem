"""FORGIA pezzo #171 — `WakeAgent._apply_lateral_inhibition`.

Greedy filter applied AFTER ranked selection: a skill is kept iff
no already-kept skill registers it as antagonist (and vice versa).
This implements Földiák (1990) winner-take-all-with-inhibition on
the retrieval frontier.
"""
from __future__ import annotations

from pathlib import Path

from verimem.memory import EpisodicMemory
from verimem.skill import Skill, SkillLibrary
from verimem.wake import WakeAgent


def _build(tmp_path: Path) -> WakeAgent:
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    skills = SkillLibrary(
        dir_path=tmp_path / "sk", db_path=tmp_path / "sk" / "idx.db",
    )
    return WakeAgent(memory=mem, skills=skills)


def test_inhibition_no_antagonists_noop(tmp_path: Path):
    wake = _build(tmp_path)
    wake.skills.store(Skill(id="A", name="a", trigger="t", body="b"))
    wake.skills.store(Skill(id="B", name="b", trigger="t", body="b"))
    a = wake.skills.get("A")
    b = wake.skills.get("B")
    out = wake._apply_lateral_inhibition([a, b])
    assert [s.id for s in out] == ["A", "B"]


def test_inhibition_skips_antagonist_of_selected(tmp_path: Path):
    """A is selected first; B (antagonist of A) is skipped."""
    wake = _build(tmp_path)
    wake.skills.store(Skill(id="A", name="a", trigger="t", body="b",
                             antagonists=["B"]))
    wake.skills.store(Skill(id="B", name="b", trigger="t", body="b",
                             antagonists=["A"]))
    wake.skills.store(Skill(id="C", name="c", trigger="t", body="b"))
    a = wake.skills.get("A")
    b = wake.skills.get("B")
    c = wake.skills.get("C")
    # Order matters: A first, B is antagonist → skipped, C survives.
    out = wake._apply_lateral_inhibition([a, b, c])
    assert [s.id for s in out] == ["A", "C"]


def test_inhibition_asymmetric_antagonist_still_blocks(tmp_path: Path):
    """If only A→B is recorded (not B→A), A is still considered antagonist
    of B because the relation is mutual semantically."""
    wake = _build(tmp_path)
    # A doesn't list B but B lists A — second-pick B blocked by first A
    wake.skills.store(Skill(id="A", name="a", trigger="t", body="b"))
    wake.skills.store(Skill(id="B", name="b", trigger="t", body="b",
                             antagonists=["A"]))
    a = wake.skills.get("A")
    b = wake.skills.get("B")
    out = wake._apply_lateral_inhibition([a, b])
    assert [s.id for s in out] == ["A"]


def test_inhibition_chain(tmp_path: Path):
    """A blocks B; C is unrelated → A and C kept, B dropped."""
    wake = _build(tmp_path)
    wake.skills.store(Skill(id="A", name="a", trigger="t", body="b",
                             antagonists=["B"]))
    wake.skills.store(Skill(id="B", name="b", trigger="t", body="b"))
    wake.skills.store(Skill(id="C", name="c", trigger="t", body="b"))
    wake.skills.store(Skill(id="D", name="d", trigger="t", body="b",
                             antagonists=["C"]))
    a = wake.skills.get("A")
    b = wake.skills.get("B")
    c = wake.skills.get("C")
    d = wake.skills.get("D")
    out = wake._apply_lateral_inhibition([a, b, c, d])
    assert [s.id for s in out] == ["A", "C"]


def test_inhibition_empty_input(tmp_path: Path):
    wake = _build(tmp_path)
    assert wake._apply_lateral_inhibition([]) == []
