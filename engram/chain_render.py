"""STRIPS chain markdown renderer.

FORGIA pezzo #242 — Wave 41. Renders a plan (output of plan_strips
or chain_validate) as readable markdown for chat-UI display.
Pure-string utility.
"""
from __future__ import annotations

from collections.abc import Iterable

from .skill import Skill


def render_chain_markdown(
    *,
    initial_state: Iterable[str],
    chain: list[Skill],
    goal_state: Iterable[str] | None = None,
) -> str:
    """Format a STRIPS plan as markdown.

    Output:
      ## Plan: N steps
      **Initial state**: {pred1, pred2}
      | Step | Skill | Pre | Post |
      |------|-------|-----|------|
      | 1 | auth | have_creds | logged_in |
      ...
      **Final state**: {...}
      **Goal**: ✓/✗
    """
    state = set(initial_state)
    lines: list[str] = []
    lines.append(f"## Plan: {len(chain)} step{'s' if len(chain) != 1 else ''}")
    lines.append("")
    lines.append(
        f"**Initial state**: `{sorted(state) if state else '(empty)'}`"
    )
    lines.append("")

    if chain:
        lines.append("| Step | Skill | Pre check | Post effect |")
        lines.append("|------|-------|-----------|-------------|")
        for i, sk in enumerate(chain, start=1):
            pre = sorted(sk.preconditions or [])
            post = sorted(sk.postconditions or [])
            pre_ok = set(pre).issubset(state)
            check = "✓" if pre_ok else "✗"
            pre_str = ", ".join(pre) if pre else "(none)"
            post_str = ", ".join(post) if post else "(none)"
            lines.append(
                f"| {i} | {sk.name} (`{sk.id}`) | "
                f"{check} {pre_str} | + {post_str} |"
            )
            # Update state for the next row's pre-check.
            if pre_ok:
                state |= set(post)
        lines.append("")

    lines.append(
        f"**Final state**: `{sorted(state) if state else '(empty)'}`"
    )

    if goal_state is not None:
        goal_set = set(goal_state)
        ok = goal_set.issubset(state)
        marker = "✓" if ok else "✗"
        lines.append("")
        status = "satisfied" if ok else "NOT satisfied"
        missing = sorted(goal_set - state)
        lines.append(
            f"**Goal** ({sorted(goal_set)}): {marker} {status}"
            + (f" — missing {missing}" if missing else "")
        )

    return "\n".join(lines)


__all__ = ["render_chain_markdown"]
