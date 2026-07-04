"""Batch portable export of skills.

FORGIA pezzo #228 — Wave 27. Existing per-skill export tool
returns one record. This returns the entire library (or filtered
subset) as a single payload, ready for backup or migration.

Excludes transient fields (learned_embedding, compiled_macro) by
default — they're large and installation-specific. Pass
`include_transient=True` to keep them.
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .skill import Skill, SkillStatus

_SCHEMA_VERSION = 2  # bump when the skill schema changes


_TRANSIENT_FIELDS = ("learned_embedding", "compiled_macro")


def export_all_skills(
    skills: list[Skill],
    *,
    status: SkillStatus | None = None,
    include_transient: bool = False,
) -> dict[str, Any]:
    """Return all skills as portable JSON-compatible dicts.

    Args:
      - `skills`: full skill pool.
      - `status`: optional filter.
      - `include_transient`: include `learned_embedding` and
        `compiled_macro` in the dump (default False — they're large
        and installation-specific).

    Returns: `{schema_version, n_total, skills: [...]}`.
    """
    rows: list[dict[str, Any]] = []
    for s in skills:
        if status is not None and s.status != status:
            continue
        d = asdict(s)
        if not include_transient:
            for f in _TRANSIENT_FIELDS:
                d.pop(f, None)
        rows.append(d)
    return {
        "schema_version": _SCHEMA_VERSION,
        "n_total": len(rows),
        "skills": rows,
    }


__all__ = ["export_all_skills"]
