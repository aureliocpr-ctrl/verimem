"""Deterministic self_model refresh (cycle #68).

Updates the self_model with information that can be derived without
natural-language reasoning:

  - `active_projects`: top-K second-segment of `project/<name>/...`
    topic prefixes seen in the last N episodes.
  - `recent_focus`: task_text of the most recent episode (truncated).

Preserves verbatim the fields that DO require interpretation:
  - current_goals, open_decisions, collab_style, notes

For LLM-driven updates of the preserved fields, plug the proposed
content into the existing Hippo Dreams pipeline (cycle #34-#39,
subscription-first) — that's the cycle #69 candidate, out of scope here.

Pure Python, no I/O. Caller wires this against:
  - SelfModelStore.get() → `current`
  - Agent.memory.recent_episodes(lookback) → `episodes`
  - SelfModelStore.update(proposed) → write
"""
from __future__ import annotations

from collections import Counter
from typing import Any


def _extract_project_name(topic: str | None) -> str | None:
    """Return the second segment of `project/<name>/...`, or None."""
    if not topic or not isinstance(topic, str):
        return None
    parts = topic.split("/")
    if len(parts) < 2:
        return None
    if parts[0].lower() != "project":
        return None
    name = (parts[1] or "").strip()
    return name or None


def _topic_for_episode(ep: dict[str, Any]) -> str | None:
    """Best-effort topic extraction. The episode object may carry the
    topic on different keys depending on the source:
      - `topic_hint` (test fixtures)
      - `topic` (some MCP returns)
      - `task_text` may embed `[topic/...]` prefix.
    """
    for key in ("topic_hint", "topic"):
        v = ep.get(key)
        if isinstance(v, str) and v:
            return v
    task = ep.get("task_text") or ""
    if isinstance(task, str) and task.startswith("[") and "]" in task:
        # `[project/engram/foo] rest...` → extract bracketed part
        end = task.index("]")
        return task[1:end]
    return None


def _truncate(s: str, n: int = 280) -> str:
    s = (s or "").strip()
    if len(s) <= n:
        return s
    return s[:n - 1] + "…"


def propose_refresh(
    *,
    current: dict[str, Any] | None,
    episodes: list[dict[str, Any]],
    top_k_projects: int = 6,
) -> dict[str, Any]:
    """Return a proposed new content dict for the self_model.

    Args:
        current: the current self_model content (or None if never written).
        episodes: list of recent episodes, newest LAST or in any order —
                  we sort by `created_at` to find the latest.
        top_k_projects: max number of project names to keep.

    Returns:
        Proposed content dict with all six known fields. Preserved
        fields are copied verbatim from `current` (or defaulted when
        `current is None`). Derived fields are recomputed.
    """
    if not episodes:
        # No signal — return current unchanged (or empty defaults).
        if current is None:
            return {
                "current_goals": [],
                "open_decisions": [],
                "active_projects": [],
                "collab_style": "",
                "recent_focus": "",
                "notes": "",
            }
        return dict(current)

    # ---- derive active_projects from topic frequency ------------
    name_counts: Counter[str] = Counter()
    for ep in episodes:
        topic = _topic_for_episode(ep)
        name = _extract_project_name(topic)
        if name:
            name_counts[name] += 1
    active = [name for name, _ in name_counts.most_common(top_k_projects)]

    # ---- derive recent_focus from latest episode ---------------
    try:
        latest = max(
            episodes,
            key=lambda e: float(e.get("created_at") or 0.0),
        )
    except (TypeError, ValueError):
        latest = episodes[-1]
    recent_focus = _truncate(str(latest.get("task_text") or ""))

    # ---- preserve immutable fields -----------------------------
    if current is None:
        preserved = {
            "current_goals": [],
            "open_decisions": [],
            "collab_style": "",
            "notes": "",
        }
    else:
        preserved = {
            "current_goals": current.get("current_goals", []),
            "open_decisions": current.get("open_decisions", []),
            "collab_style": current.get("collab_style", ""),
            "notes": current.get("notes", ""),
        }

    return {
        **preserved,
        "active_projects": active,
        "recent_focus": recent_focus,
    }


def compute_diff(
    a: dict[str, Any], b: dict[str, Any],
) -> list[str]:
    """Return the sorted list of top-level field names whose value differs
    between `a` and `b`. Used by the MCP tool to summarise the refresh."""
    changed: list[str] = []
    for key in sorted(set(a.keys()) | set(b.keys())):
        if a.get(key) != b.get(key):
            changed.append(key)
    return changed


__all__ = ["propose_refresh", "compute_diff"]
