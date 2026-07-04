"""Atomic skill-pair merge for de-duplication.

FORGIA pezzo #254 — Wave 53. Apply find_duplicate_skills (#232)
suggestions: fold secondary skill into primary, accumulate
trials/successes, retire secondary, record lineage edge.
"""
from __future__ import annotations

from typing import Any


def merge_skill_pair(
    *,
    skill_id_a: str,
    skill_id_b: str,
    agent: Any,
    keeper: str = "a",
    apply: bool = False,
) -> dict[str, Any]:
    """Merge two skills atomically.

    Args:
      - `skill_id_a`, `skill_id_b`: the duplicate pair.
      - `keeper`: which one to keep as primary ('a' or 'b').
      - `apply`: when True, mutate via skills.store().

    Returns: `{ok, primary_id, secondary_id, proposed_trials,
    proposed_successes, applied}`.
    """
    skills_store = getattr(agent, "skills", None)
    if skills_store is None:
        return {
            "ok": False, "primary_id": "", "secondary_id": "",
            "applied": False,
        }

    sk_a = skills_store.get(skill_id_a)
    sk_b = skills_store.get(skill_id_b)
    if sk_a is None or sk_b is None:
        return {
            "ok": False,
            "primary_id": skill_id_a if keeper == "a" else skill_id_b,
            "secondary_id": skill_id_b if keeper == "a" else skill_id_a,
            "missing": [
                sid for sid, sk in [(skill_id_a, sk_a), (skill_id_b, sk_b)]
                if sk is None
            ],
            "applied": False,
        }

    primary, secondary = (sk_a, sk_b) if keeper == "a" else (sk_b, sk_a)

    new_trials = int(primary.trials) + int(secondary.trials)
    new_successes = int(primary.successes) + int(secondary.successes)
    new_parents = list(primary.parent_skills)
    if secondary.id not in new_parents:
        new_parents.append(secondary.id)

    applied = False
    if apply:
        primary.trials = new_trials
        primary.successes = new_successes
        primary.parent_skills = new_parents
        secondary.status = "retired"
        try:
            skills_store.store(primary)
            skills_store.store(secondary)
            applied = True
        except Exception:
            applied = False

    return {
        "ok": True,
        "primary_id": primary.id,
        "secondary_id": secondary.id,
        "proposed_trials": new_trials,
        "proposed_successes": new_successes,
        "proposed_parent_skills": new_parents,
        "applied": applied,
    }


__all__ = ["merge_skill_pair"]
