"""R27: Render a skill chain as markdown.

Input: a plan list (e.g. output of skill_composer.compose_plan),
each entry has skill_id + role + trigger + optional match_score.

Output: markdown string with step-by-step + arrow + role markers.
"""
from __future__ import annotations

from typing import Any


def render_chain(plan: list[dict[str, Any]]) -> str:
    """Render a skill chain as markdown."""
    if not plan:
        return ""

    lines: list[str] = ["## Auto-generated skill chain", ""]
    for i, step in enumerate(plan, start=1):
        sid = step.get("skill_id", "?")
        role = step.get("role", "matched")
        trigger = (step.get("trigger") or "")[:80]
        marker = "▶" if role == "matched" else "│"
        score_str = ""
        ms = step.get("match_score")
        if isinstance(ms, (int, float)) and ms > 0:
            score_str = f" [score={ms:.2f}]"
        lines.append(
            f"{i}. {marker} `{sid}` ({role}){score_str}"
        )
        if trigger:
            lines.append(f"   _trigger: {trigger}_")
        if i < len(plan):
            lines.append("   ↓")
    return "\n".join(lines)


__all__ = ["render_chain"]
