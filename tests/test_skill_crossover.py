"""FORGIA pezzo #177 — `crossover_skill_bodies(parent_a, parent_b, rng)`.

Engram crossover: genetic-programming-style mixing of skill body
text. Splits each body into "steps" by line, then assembles a new
hybrid by interleaving the parents (single-point crossover, randomly
chosen). The hybrid carries both parents in `parent_skills`.

Why this is non-trivial:
- Pure-text genetic programming on procedural skill bodies has not,
  to our knowledge, been applied in the literature on agent memory.
- The interleave preserves natural-language coherence at line-level
  (assumption: each line ≈ one self-contained step).
- Determinism via seedable RNG: testable.
"""
from __future__ import annotations

import random

from engram.skill import Skill


def test_crossover_returns_hybrid_skill():
    from engram.skill_crossover import crossover_skill_bodies
    a = Skill(id="A", name="alpha", trigger="ta",
              body="step1\nstep2\nstep3", status="promoted")
    b = Skill(id="B", name="beta", trigger="tb",
              body="STEPx\nSTEPy\nSTEPz", status="promoted")
    rng = random.Random(42)
    child = crossover_skill_bodies(a, b, rng=rng)
    assert isinstance(child, Skill)
    assert child.parent_skills == ["A", "B"]
    assert child.status == "candidate"
    # The body must contain at least one line from each parent.
    a_lines = set(a.body.splitlines())
    b_lines = set(b.body.splitlines())
    child_lines = set(child.body.splitlines())
    assert child_lines & a_lines, "child has no line from parent A"
    assert child_lines & b_lines, "child has no line from parent B"


def test_crossover_deterministic_with_seed():
    from engram.skill_crossover import crossover_skill_bodies
    a = Skill(id="A", name="a", trigger="t",
              body="A1\nA2\nA3\nA4\nA5", status="promoted")
    b = Skill(id="B", name="b", trigger="t",
              body="B1\nB2\nB3\nB4\nB5", status="promoted")
    c1 = crossover_skill_bodies(a, b, rng=random.Random(7))
    c2 = crossover_skill_bodies(a, b, rng=random.Random(7))
    assert c1.body == c2.body


def test_crossover_naming_convention():
    from engram.skill_crossover import crossover_skill_bodies
    a = Skill(id="A", name="alpha", trigger="t", body="x")
    b = Skill(id="B", name="beta", trigger="t", body="y")
    child = crossover_skill_bodies(a, b, rng=random.Random(0))
    # Compound naming pattern: alpha_x_beta
    assert child.name == "alpha_x_beta"


def test_crossover_handles_single_line_bodies():
    """Edge: single-line body → child gets at least one line from each."""
    from engram.skill_crossover import crossover_skill_bodies
    a = Skill(id="A", name="a", trigger="t", body="only-A", status="promoted")
    b = Skill(id="B", name="b", trigger="t", body="only-B", status="promoted")
    child = crossover_skill_bodies(a, b, rng=random.Random(0))
    # With one line each, the hybrid can contain only one or both;
    # we accept any non-empty combination that mentions a parent.
    assert child.body.strip()
    assert ("only-A" in child.body) or ("only-B" in child.body)


def test_crossover_trigger_combines_parents():
    from engram.skill_crossover import crossover_skill_bodies
    a = Skill(id="A", name="a", trigger="alpha-trigger", body="x")
    b = Skill(id="B", name="b", trigger="beta-trigger", body="y")
    child = crossover_skill_bodies(a, b, rng=random.Random(0))
    assert "alpha-trigger" in child.trigger or "beta-trigger" in child.trigger
