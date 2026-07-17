"""Step-by-step validation of a skill chain (STRIPS plan).

FORGIA pezzo #223 — Wave 22. Given an initial state and a proposed
skill chain, simulate applying it skill-by-skill, verifying that
each precondition holds before applying postconditions.

Useful for sanity-checking manually-constructed plans, debugging
broken STRIPS chains, and explaining failures to the user.
"""
from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .skill import Skill


def validate_chain(
    *,
    initial_state: Iterable[str],
    skill_chain: list[Skill],
) -> dict[str, Any]:
    """Simulate the chain step-by-step.

    Args:
      - `initial_state`: predicates currently true.
      - `skill_chain`: ordered list of Skill instances to apply.

    Returns: dict with
      - `valid`: bool — True iff every step's preconditions held.
      - `broken_at`: int | None — index of the first skill whose
        preconditions were unmet (None if valid).
      - `final_state`: sorted list of predicates true at the end
        (or at the break point if invalid).
      - `steps`: list of `{step_index, skill_id, skill_name,
        applied: bool, state_before, state_after, missing_pre}`.
      - `reason`: human-readable explanation if invalid; empty
        string if valid.
    """
    state = set(initial_state)
    steps: list[dict[str, Any]] = []
    broken_at: int | None = None
    reason = ""

    for i, sk in enumerate(skill_chain):
        pre = set(sk.preconditions or [])
        state_before = sorted(state)
        missing = sorted(pre - state)
        if missing:
            broken_at = i
            reason = (
                f"Skill {sk.id} ({sk.name}) at step {i} requires "
                f"{missing!r} but state has {state_before!r}"
            )
            steps.append({
                "step_index": i,
                "skill_id": sk.id,
                "skill_name": sk.name,
                "applied": False,
                "state_before": state_before,
                "state_after": state_before,  # unchanged
                "missing_pre": missing,
            })
            break
        # Apply.
        post = set(sk.postconditions or [])
        state |= post
        steps.append({
            "step_index": i,
            "skill_id": sk.id,
            "skill_name": sk.name,
            "applied": True,
            "state_before": state_before,
            "state_after": sorted(state),
            "missing_pre": [],
        })

    return {
        "valid": broken_at is None,
        "broken_at": broken_at,
        "final_state": sorted(state),
        "steps": steps,
        "reason": reason,
    }


__all__ = ["validate_chain"]
