"""R17: Episode diff at metadata level.

Compare two arbitrary episodes field-by-field. Returns:
  - diff_fields: list of fields that differ
  - summary: human-readable one-liner
  - a, b: snapshots
"""
from __future__ import annotations

from typing import Any

_COMPARE_FIELDS = (
    "id", "task_text", "outcome", "skills_used", "tokens_used",
    "num_steps", "final_answer",
)


def _snapshot(ep: Any) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for f in _COMPARE_FIELDS:
        out[f] = getattr(ep, f, None)
    return out


def episode_diff(a: Any, b: Any) -> dict[str, Any]:
    """Return a structured diff of two episodes."""
    sa = _snapshot(a)
    sb = _snapshot(b)
    diff_fields: list[str] = []
    for f in _COMPARE_FIELDS:
        va, vb = sa.get(f), sb.get(f)
        if isinstance(va, list) and isinstance(vb, list):
            if sorted(va) != sorted(vb):
                diff_fields.append(f)
        elif va != vb:
            diff_fields.append(f)

    pieces: list[str] = []
    if "outcome" in diff_fields:
        pieces.append(f"outcome ({sa['outcome']} vs {sb['outcome']})")
    if "skills_used" in diff_fields:
        pieces.append("skills differ")
    if "tokens_used" in diff_fields:
        pieces.append(f"tokens ({sa.get('tokens_used', 0)} vs "
                      f"{sb.get('tokens_used', 0)})")
    summary = "; ".join(pieces) if pieces else "metadata identical"

    return {
        "diff_fields": diff_fields,
        "summary": summary,
        "a": sa,
        "b": sb,
    }


__all__ = ["episode_diff"]
