"""R1.2: Render trajectory as markdown.

Uses kind-specific markers for fast visual scanning:
  - thought:    🧠 (or "thought")
  - action:     ⚡ tool call with args/result
  - observation: 👁 passive intake
  - decision:   🔀 branch point with branch_id

For long tool_result the content is truncated to keep render bounded.
"""
from __future__ import annotations

import json

from .trajectory import TrajectoryStep, trajectory_normalize

_KIND_PREFIX = {
    "thought": "🧠 thought",
    "action": "⚡ action",
    "observation": "👁 observation",
    "decision": "🔀 decision",
}


def _truncate(s: str | None, n: int) -> str:
    if s is None:
        return ""
    if len(s) <= n:
        return s
    return s[:n] + f"... [truncated {len(s) - n} chars]"


def trajectory_to_markdown(
    steps: list[TrajectoryStep],
    *,
    max_tool_result_chars: int = 1000,
) -> str:
    """Render trajectory as markdown step-by-step trace."""
    if not steps:
        return ""

    sorted_steps = trajectory_normalize(steps)
    lines: list[str] = []
    for s in sorted_steps:
        prefix = _KIND_PREFIX.get(s.kind, s.kind)
        head = f"### Step {s.step_idx} — {prefix}"
        if s.branch_id:
            head += f"  `[branch={s.branch_id}]`"
        lines.append(head)
        lines.append("")
        lines.append(s.content)
        if s.kind == "action" and s.tool_name:
            lines.append("")
            lines.append(f"**tool**: `{s.tool_name}`")
            if s.tool_args:
                try:
                    args_str = json.dumps(s.tool_args, default=str)[:300]
                except Exception:
                    args_str = str(s.tool_args)[:300]
                lines.append(f"**args**: `{args_str}`")
            if s.tool_result:
                truncated = _truncate(s.tool_result, max_tool_result_chars)
                lines.append("**result**:")
                lines.append("```")
                lines.append(truncated)
                lines.append("```")
        lines.append("")
    return "\n".join(lines)


def trajectory_summary_line(
    steps: list[TrajectoryStep],
) -> str:
    """One-line summary: counts + branches.

    Example: '4 steps (1T/1A/1O/1D) branches=[ssh-path]'.
    """
    if not steps:
        return "0 steps"
    by_kind: dict[str, int] = {}
    branches: set[str] = set()
    for s in steps:
        by_kind[s.kind] = by_kind.get(s.kind, 0) + 1
        if s.branch_id:
            branches.add(s.branch_id)
    parts: list[str] = []
    for k in ("thought", "action", "observation", "decision"):
        n = by_kind.get(k, 0)
        parts.append(f"{n}{k[0].upper()}")
    line = f"{len(steps)} steps ({'/'.join(parts)})"
    if branches:
        line += f" branches=[{','.join(sorted(branches))}]"
    return line


__all__ = ["trajectory_to_markdown", "trajectory_summary_line"]
