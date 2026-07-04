"""Tests for the skill library: persistence, fitness, lifecycle, lineage, dedup."""
from __future__ import annotations

from engram.skill import Skill, SkillLibrary


def test_store_and_retrieve(tmp_data_dir):
    lib = SkillLibrary(tmp_data_dir / "skills", tmp_data_dir / "skills" / "idx.db")
    s = Skill(name="recursion-fast-fib", trigger="when computing fibonacci or DP",
              body="use memoization", rationale="avoids exponential blowup")
    lib.store(s)
    assert lib.get(s.id) is not None
    out = lib.retrieve("compute Fibonacci numbers", k=1)
    assert len(out) == 1
    assert out[0].id == s.id


def test_bayesian_fitness_prior(tmp_data_dir):
    lib = SkillLibrary(tmp_data_dir / "skills", tmp_data_dir / "skills" / "idx.db")
    s = Skill(name="x", trigger="x", body="x")
    lib.store(s)
    # No trials → fitness equals prior mean (1/2 for Beta(1,1))
    assert abs(s.fitness_mean - 0.5) < 1e-9


def test_promote_after_threshold(tmp_data_dir):
    lib = SkillLibrary(tmp_data_dir / "skills", tmp_data_dir / "skills" / "idx.db")
    s = Skill(name="ok", trigger="ok", body="ok")
    lib.store(s)
    for _ in range(4):
        lib.update_fitness(s.id, success=True, tokens=100)
    promoted, retired = lib.promote_or_retire()
    assert s.id in promoted
    assert lib.get(s.id).status == "promoted"


def test_retire_low_fitness(tmp_data_dir):
    lib = SkillLibrary(tmp_data_dir / "skills", tmp_data_dir / "skills" / "idx.db")
    s = Skill(name="bad", trigger="bad", body="bad")
    lib.store(s)
    for _ in range(5):
        lib.update_fitness(s.id, success=False, tokens=100)
    promoted, retired = lib.promote_or_retire()
    assert s.id in retired
    assert lib.get(s.id).status == "retired"


def test_lineage_graph(tmp_data_dir):
    lib = SkillLibrary(tmp_data_dir / "skills", tmp_data_dir / "skills" / "idx.db")
    a = Skill(name="A", trigger="A", body="A"); lib.store(a)
    b = Skill(name="B", trigger="B", body="B"); lib.store(b)
    hybrid = Skill(name="A+B", trigger="hybrid", body="x", parent_skills=[a.id, b.id])
    lib.store(hybrid)
    g = lib.lineage_graph()
    assert g.has_edge(a.id, hybrid.id)
    assert g.has_edge(b.id, hybrid.id)


def test_find_duplicates(tmp_data_dir):
    lib = SkillLibrary(tmp_data_dir / "skills", tmp_data_dir / "skills" / "idx.db")
    a = Skill(name="reverse a list",
              trigger="when you need to reverse the order of items in a list", body="x")
    b = Skill(name="reverse a list",
              trigger="when you need to reverse the order of items in a list", body="y")
    lib.store(a); lib.store(b)
    dups = lib.find_duplicates(threshold=0.85)
    assert len(dups) >= 1
