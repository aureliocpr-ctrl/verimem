"""FORGIA pezzo #177 — Engram crossover for procedural skills.

Genetic-programming-style mixing of skill body text. Splits each
parent body into "steps" by line, picks a single crossover point,
and assembles the child by taking the prefix from one parent and
the suffix from the other.

Inspired by:
- Koza (1992) Genetic Programming on tree-structured programs.
- Mendelian inheritance: chromosomes recombine at a single locus.

The novelty here is applying single-point crossover to natural-
language *procedural* skill bodies (vs. AST or tree). It assumes
each line of a skill body is a self-contained step, which holds
for the procedural-skill format used by HippoAgent.
"""
from __future__ import annotations

import random
import uuid

from .skill import Skill


def crossover_skill_bodies(
    parent_a: Skill,
    parent_b: Skill,
    *,
    rng: random.Random | None = None,
) -> Skill:
    """Single-point crossover on procedural skill bodies.

    Returns a NEW Skill whose body is `prefix(P) ⊕ suffix(Q)` where
    P and Q are randomly chosen between (parent_a, parent_b). The
    child carries both parents in `parent_skills` and starts as
    `status="candidate"` so it enters the standard fitness pipeline.

    Naming convention: ``{a.name}_x_{b.name}``.
    """
    rng = rng or random.Random()
    a_lines = parent_a.body.splitlines() or [parent_a.body]
    b_lines = parent_b.body.splitlines() or [parent_b.body]

    # Decide which parent contributes the prefix.
    if rng.random() < 0.5:
        front, back = a_lines, b_lines
        front_origin, back_origin = "A", "B"
    else:
        front, back = b_lines, a_lines
        front_origin, back_origin = "B", "A"

    # Pick crossover points within each parent — at least 1 line from
    # each side so the child contains material from both.
    front_cut = rng.randint(1, max(1, len(front)))
    back_cut = rng.randint(0, max(0, len(back) - 1))
    child_body_lines = front[:front_cut] + back[back_cut:]
    if not child_body_lines:
        child_body_lines = [parent_a.body, parent_b.body]
    child_body = "\n".join(child_body_lines)

    # Trigger: pick from front-origin parent (deterministic given rng).
    child_trigger = (
        parent_a.trigger if front_origin == "A" else parent_b.trigger
    )

    return Skill(
        id=uuid.uuid4().hex[:12],
        name=f"{parent_a.name}_x_{parent_b.name}",
        trigger=child_trigger,
        body=child_body,
        rationale=(
            f"Engram crossover: prefix from {parent_a.name if front_origin == 'A' else parent_b.name} "
            f"(cut at line {front_cut}), suffix from "
            f"{parent_a.name if back_origin == 'A' else parent_b.name} "
            f"(cut at line {back_cut})."
        ),
        status="candidate",
        stage="rem",
        parent_skills=[parent_a.id, parent_b.id],
    )
