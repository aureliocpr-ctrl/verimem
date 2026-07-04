"""Deep-clone of a skill for A/B testing.

FORGIA pezzo #240 — Wave 39. Clone an existing skill into a fresh
candidate so the user can modify the clone (body, predicates,
trigger) without touching the production version.

The clone inherits content but starts with:
  - fresh id (uuid)
  - empty trials/successes (clean slate, must earn promotion)
  - status = "candidate"
  - parent_skills includes the original
  - no compiled_macro (would be misleading without empirical signal)
"""
from __future__ import annotations

import time
import uuid

from .skill import Skill


def clone_skill(
    original: Skill,
    *,
    new_name: str | None = None,
) -> Skill:
    """Deep-clone a skill into a fresh candidate.

    Args:
      - `original`: the skill to clone.
      - `new_name`: optional override for the clone's name. When
        None, the clone keeps the same `name` as the original.
    """
    return Skill(
        id=uuid.uuid4().hex[:12],
        version=1,
        name=new_name if new_name else original.name,
        trigger=original.trigger,
        body=original.body,
        rationale=original.rationale,
        stage=original.stage,
        provenance_episodes=list(original.provenance_episodes),
        parent_skills=[original.id] + list(original.parent_skills),
        status="candidate",
        trials=0,
        successes=0,
        avg_tokens=0.0,
        created_at=time.time(),
        updated_at=time.time(),
        learned_embedding=None,
        compiled_macro=None,
        is_counterfactual=original.is_counterfactual,
        practice_prompts=list(original.practice_prompts),
        last_used_at=0.0,
        antagonists=list(original.antagonists),
        preconditions=list(original.preconditions),
        postconditions=list(original.postconditions),
    )


__all__ = ["clone_skill"]
