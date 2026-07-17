"""FORGIA pezzo #178 — `SleepEngine._stage_crossover`.

Generates `n_pairs` engram-crossover hybrids from the top-fitness
skills, stores them as `status="candidate"` for the standard
fitness pipeline. Zero LLM cost. Cabled behind
`CONFIG.crossover_enabled`.
"""
from __future__ import annotations

from pathlib import Path

from verimem.episode import Episode, Trace
from verimem.memory import EpisodicMemory
from verimem.semantic import SemanticMemory
from verimem.skill import Skill, SkillLibrary
from verimem.sleep import SleepEngine, SleepReport


def _build(tmp_path: Path) -> SleepEngine:
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    skills = SkillLibrary(
        dir_path=tmp_path / "sk", db_path=tmp_path / "sk" / "idx.db",
    )
    sem = SemanticMemory(db_path=tmp_path / "sem.db")
    eng = SleepEngine(memory=mem, skills=skills, semantic=sem, seed=42)
    return eng


def test_crossover_skips_when_too_few_skills(tmp_path: Path):
    eng = _build(tmp_path)
    eng.skills.store(Skill(id="A", name="a", trigger="t",
                            body="line1\nline2", status="promoted",
                            trials=10, successes=9))
    report = SleepReport()
    eng._stage_crossover(report, n_pairs=3, top_k=5)
    assert report.n_crossovers == 0


def test_crossover_generates_hybrid_pairs(tmp_path: Path):
    eng = _build(tmp_path)
    for i in range(5):
        eng.skills.store(Skill(
            id=f"S{i}", name=f"sk{i}", trigger=f"t{i}",
            body=f"step{i}_a\nstep{i}_b\nstep{i}_c",
            status="promoted", trials=10, successes=9,
        ))
    report = SleepReport()
    eng._stage_crossover(report, n_pairs=2, top_k=5)
    assert report.n_crossovers == 2
    hybrids = [s for s in eng.skills.all() if "_x_" in s.name]
    assert len(hybrids) == 2
    # Each hybrid has exactly 2 parents.
    for h in hybrids:
        assert len(h.parent_skills) == 2
        assert h.status == "candidate"


def test_crossover_picks_high_fitness_skills(tmp_path: Path):
    """Crossover selects from top_k by fitness, not arbitrary."""
    eng = _build(tmp_path)
    # 10 skills with descending fitness — top 3 dominate.
    for i in range(10):
        successes = 19 - i  # 19, 18, ... 10
        eng.skills.store(Skill(
            id=f"S{i}", name=f"sk{i}", trigger=f"t{i}",
            body=f"line{i}",
            status="promoted", trials=20, successes=successes,
        ))
    report = SleepReport()
    eng._stage_crossover(report, n_pairs=3, top_k=3)
    hybrids = [s for s in eng.skills.all() if "_x_" in s.name]
    # All hybrids should have parents drawn from {S0, S1, S2}.
    top_ids = {"S0", "S1", "S2"}
    for h in hybrids:
        assert set(h.parent_skills).issubset(top_ids), (
            f"hybrid {h.name} has parents outside top_3: {h.parent_skills}"
        )


def test_crossover_does_not_create_self_pair(tmp_path: Path):
    """A skill cannot crossover with itself."""
    eng = _build(tmp_path)
    for i in range(2):
        eng.skills.store(Skill(
            id=f"S{i}", name=f"sk{i}", trigger="t",
            body=f"a{i}\nb{i}",
            status="promoted", trials=10, successes=9,
        ))
    report = SleepReport()
    eng._stage_crossover(report, n_pairs=5, top_k=2)
    hybrids = [s for s in eng.skills.all() if "_x_" in s.name]
    for h in hybrids:
        assert h.parent_skills[0] != h.parent_skills[1]
