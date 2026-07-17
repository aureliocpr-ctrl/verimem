"""Compact human-readable episode TL;DR.

FORGIA pezzo #246 — Wave 45. Renders a one-liner for an episode
suitable for UI lists. Format:
  `[✓|✗] task_text… (N skills, T tok, YYYY-MM-DD)`
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

_MAX_TASK_LEN = 120


def summarize_episode(episode: Any) -> str:
    """Single-line summary."""
    outcome = getattr(episode, "outcome", "")
    marker = {
        "success": "✓",
        "failure": "✗",
    }.get(outcome, "?")

    task = (getattr(episode, "task_text", "") or "")
    if len(task) > _MAX_TASK_LEN:
        task = task[: _MAX_TASK_LEN - 1] + "…"

    n_skills = len(getattr(episode, "skills_used", None) or [])
    tokens = int(getattr(episode, "tokens_used", 0) or 0)
    ts = float(getattr(episode, "created_at", 0.0) or 0.0)
    date_str = ""
    if ts > 0:
        try:
            date_str = datetime.fromtimestamp(
                ts, tz=timezone.utc
            ).strftime("%Y-%m-%d")
        except Exception:
            date_str = ""

    meta_parts: list[str] = []
    meta_parts.append(f"{n_skills} skill" + ("s" if n_skills != 1 else ""))
    if tokens > 0:
        meta_parts.append(f"{tokens} tok")
    if date_str:
        meta_parts.append(date_str)
    meta = ", ".join(meta_parts)

    return f"[{marker}] {task} ({meta})"


def summarize_episodes(episodes: list[Any]) -> list[str]:
    """Apply summarize_episode to a list."""
    return [summarize_episode(ep) for ep in episodes]


__all__ = ["summarize_episode", "summarize_episodes"]
