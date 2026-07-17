"""Compose N ordered skills into a single SCHEMA meta-skill.

FORGIA pezzo #235 — Wave 34. Useful when the user observes a stable
recurrent sequence and wants to consolidate it into a single
callable unit. The composed skill inherits:
  - preconditions: from the FIRST skill (chain entry requirements)
  - postconditions: from the LAST skill (chain effects)
  - lineage: all input skills as parent_skills
  - stage: "schema"
  - status: "candidate" (must earn promotion through trials)
"""
from __future__ import annotations

import uuid

from .skill import Skill


def compose_macro(
    skills: list[Skill],
    *,
    name: str | None = None,
    trigger: str | None = None,
    stage: str = "schema",
) -> Skill | None:
    """Synthesise a meta-skill from an ordered chain.

    Args:
      - `skills`: ordered list of constituent skills (must be ≥ 2).
      - `name`: optional override; default = "macro:A->B->C".
      - `trigger`: optional override; default = constituent triggers
        joined by " | ".
      - `stage`: SkillStage tag (default "schema").

    Returns: a new Skill instance OR None if `len(skills) < 2`.
    The caller is responsible for storing it via `skills.store()`.
    """
    if len(skills) < 2:
        return None

    auto_name = "macro:" + "->".join(
        (s.name or s.id) for s in skills
    )
    auto_trigger = " | ".join((s.trigger or "") for s in skills)
    body_lines = ["Apply the following skills in order:"]
    for i, s in enumerate(skills, start=1):
        body_lines.append(f"  {i}. {s.name} ({s.id})")
    body = "\n".join(body_lines)

    composed = Skill(
        id=uuid.uuid4().hex[:12],
        name=name or auto_name,
        trigger=trigger or auto_trigger,
        body=body,
        rationale=(
            "Composed schema from "
            f"{len(skills)} constituent skills"
        ),
        stage=stage,
        status="candidate",
        parent_skills=[s.id for s in skills],
        preconditions=list(skills[0].preconditions or []),
        postconditions=list(skills[-1].postconditions or []),
    )
    return composed


__all__ = ["compose_macro"]
