"""Episode replay markdown renderer.

FORGIA pezzo #256 — Wave 55. Renders an episode as readable
markdown for chat-UI display.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def render_episode_replay(episode: Any) -> str:
    """Render episode trajectory as markdown."""
    eid = getattr(episode, "id", "")
    task = getattr(episode, "task_text", "") or ""
    answer = getattr(episode, "final_answer", "") or ""
    outcome = getattr(episode, "outcome", "")
    skills = list(getattr(episode, "skills_used", None) or [])
    tokens = int(getattr(episode, "tokens_used", 0) or 0)
    n_steps = int(getattr(episode, "num_steps", 1) or 1)
    ts = float(getattr(episode, "created_at", 0.0) or 0.0)

    marker = {"success": "✓", "failure": "✗"}.get(outcome, "?")

    lines: list[str] = []
    lines.append(f"## Episode `{eid}` {marker} `{outcome}`")

    if ts > 0:
        try:
            date_str = datetime.fromtimestamp(
                ts, tz=timezone.utc
            ).strftime("%Y-%m-%d %H:%M:%S UTC")
            lines.append(f"_{date_str}_")
        except Exception:
            pass

    lines.append("")
    lines.append(f"**Task**: {task}")
    lines.append("")

    if skills:
        lines.append(f"**Skills used** ({len(skills)}):")
        for s in skills:
            lines.append(f"  - `{s}`")
        lines.append("")
    else:
        lines.append("**Skills used**: (none — lucky guess?)")
        lines.append("")

    lines.append(f"**Steps**: {n_steps}")
    if tokens > 0:
        lines.append(f"**Tokens**: {tokens}")
    lines.append("")

    lines.append("**Final answer**:")
    lines.append("```")
    # Truncate very long answers.
    truncated = answer if len(answer) <= 2000 else answer[:2000] + "…"
    lines.append(truncated)
    lines.append("```")

    return "\n".join(lines)


__all__ = ["render_episode_replay"]
