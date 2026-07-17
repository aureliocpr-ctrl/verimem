"""Atomic export + retire skill.

FORGIA pezzo #251 — Wave 50. End-of-life flow: snapshot the skill
as portable JSON AND set status="retired" in one call. Dry-run
default.
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Any

_TRANSIENT_FIELDS = ("learned_embedding", "compiled_macro")


def archive_skill(
    *,
    skill_id: str,
    agent: Any,
    apply: bool = False,
    include_transient: bool = False,
) -> dict[str, Any]:
    """Export skill JSON + optionally retire.

    Returns: `{skill_id, found, applied, exported}`. `exported` is
    the portable JSON dict (transient fields excluded by default).
    """
    skills_store = getattr(agent, "skills", None)
    if skills_store is None:
        return {
            "skill_id": skill_id, "found": False,
            "applied": False, "exported": {},
        }
    sk = skills_store.get(skill_id)
    if sk is None:
        return {
            "skill_id": skill_id, "found": False,
            "applied": False, "exported": {},
        }

    d = asdict(sk)
    if not include_transient:
        for f in _TRANSIENT_FIELDS:
            d.pop(f, None)

    applied = False
    if apply and sk.status != "retired":
        sk.status = "retired"
        try:
            skills_store.store(sk)
            applied = True
        except Exception:
            applied = False

    return {
        "skill_id": skill_id,
        "found": True,
        "applied": applied,
        "exported": d,
    }


__all__ = ["archive_skill"]
