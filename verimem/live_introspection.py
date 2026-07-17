"""R16: Live introspection — what the agent is doing right now.

Given:
  - recent_audit: recent tool calls (list of {name, outcome, ts})
  - active_skills: skills currently triggered (list of {id, name})
  - last_recall: most recent hippo_recall result

Produce:
  - narrative: human-readable rationale
  - stage: idle / recalling / acting / learning
  - components: structured breakdown

Used as dashboard widget: "Agent X is recalling about WordPress
exploitation; CF7-RCE skill warm; about to execute exploit step."
"""
from __future__ import annotations

from typing import Any

_READ_TOOLS = {
    "hippo_recall", "hippo_facts_search", "hippo_facts_recall",
    "hippo_episode_list", "hippo_stats", "hippo_status",
    "hippo_compose_plan", "hippo_world_simulate",
}
_WRITE_TOOLS = {
    "hippo_remember", "hippo_record_episode", "hippo_skill_promote",
    "hippo_consolidate", "hippo_consolidate_light",
}


def _classify_stage(recent_audit: list[dict[str, Any]]) -> str:
    if not recent_audit:
        return "idle"
    last = recent_audit[-1].get("name", "")
    if last in _WRITE_TOOLS:
        return "learning"
    if last in _READ_TOOLS:
        return "recalling"
    if last.startswith("hippo_"):
        return "acting"
    return "idle"


def introspect_state(
    *,
    recent_audit: list[dict[str, Any]],
    active_skills: list[dict[str, Any]],
    last_recall: list[dict[str, Any]],
) -> dict[str, Any]:
    """Render the agent's current state as narrative + structured data."""
    stage = _classify_stage(recent_audit)

    lines: list[str] = []

    # Stage banner
    stage_emoji = {
        "idle": "💤", "recalling": "🧠", "acting": "⚡", "learning": "📚",
    }
    lines.append(f"### {stage_emoji.get(stage, '·')} Stage: **{stage}**")

    # Recent actions
    if recent_audit:
        lines.append("\n**Recent actions** (last 5):")
        for a in recent_audit[-5:]:
            name = a.get("name", "?")
            outcome = a.get("outcome", "?")
            marker = "✓" if outcome == "ok" else "✗"
            lines.append(f"- {marker} `{name}` → {outcome}")

    # Active skills
    if active_skills:
        lines.append("\n**Active skills:**")
        for sk in active_skills[:5]:
            sid = sk.get("id", "?")
            sname = sk.get("name", "")
            lines.append(f"- `{sid}` {sname}")

    # Last recall context
    if last_recall:
        lines.append(f"\n**Last recall** ({len(last_recall)} results):")
        for r in last_recall[:3]:
            task = r.get("task", "")[:60]
            sim = r.get("similarity", 0.0)
            out = r.get("outcome", "")
            lines.append(f"- sim={sim:.2f} [{out}] {task}")

    if not (recent_audit or active_skills or last_recall):
        lines.append("\n(no recent activity — agent idle)")

    narrative = "\n".join(lines)

    return {
        "narrative": narrative,
        "stage": stage,
        "components": {
            "n_recent_actions": len(recent_audit),
            "n_active_skills": len(active_skills),
            "n_recall_results": len(last_recall),
        },
    }


__all__ = ["introspect_state"]
