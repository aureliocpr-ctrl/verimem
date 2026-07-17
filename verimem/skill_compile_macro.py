"""Compile a SCHEMA skill into a deterministic macro.

FORGIA pezzo #253 — Wave 52. For a SCHEMA-stage skill (composed
via #235 compose_macro), extract a fast-path compiled_macro from
its parent_skills sequence. Persists on the skill so the
retrieval pipeline can short-circuit the LLM on recurring tasks.

Requirements:
  - skill.stage == "schema"
  - skill.parent_skills has ≥ 2 entries (otherwise no macro)
"""
from __future__ import annotations

import time
from typing import Any


def compile_macro(
    *,
    skill_id: str,
    agent: Any,
    apply: bool = False,
    min_parents: int = 2,
) -> dict[str, Any]:
    """Extract + optionally persist `compiled_macro` from parent_skills."""
    skills_store = getattr(agent, "skills", None)
    if skills_store is None:
        return {
            "skill_id": skill_id, "found": False,
            "compiled": False, "steps": [], "applied": False,
        }
    target = skills_store.get(skill_id)
    if target is None:
        return {
            "skill_id": skill_id, "found": False,
            "compiled": False, "steps": [], "applied": False,
        }

    if target.stage != "schema":
        return {
            "skill_id": skill_id, "found": True,
            "compiled": False,
            "reason": (
                f"skill stage is {target.stage!r}, only 'schema' "
                "skills can be compiled"
            ),
            "steps": [], "applied": False,
        }
    if len(target.parent_skills or []) < min_parents:
        return {
            "skill_id": skill_id, "found": True,
            "compiled": False,
            "reason": (
                f"need ≥ {min_parents} parent_skills to compile macro"
            ),
            "steps": [], "applied": False,
        }

    steps = []
    for parent_id in target.parent_skills:
        parent_sk = skills_store.get(parent_id)
        steps.append({
            "skill_id": parent_id,
            "name": parent_sk.name if parent_sk else "",
        })

    compiled_macro = {
        "steps": steps,
        "compiled_at": time.time(),
        "source": "parent_skills_sequence",
    }

    applied = False
    if apply:
        target.compiled_macro = compiled_macro
        try:
            skills_store.store(target)
            applied = True
        except Exception:
            applied = False

    return {
        "skill_id": skill_id,
        "found": True,
        "compiled": True,
        "steps": steps,
        "compiled_macro": compiled_macro,
        "applied": applied,
    }


__all__ = ["compile_macro"]
