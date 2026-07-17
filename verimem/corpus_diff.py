"""Timeline of changes across the 3 memory tiers since a timestamp.

FORGIA pezzo #218 — Wave 17. Useful when:
  - "what's changed since I last opened the project?"
  - "what facts has the agent learned this week?"
  - "which skills crossed promote/retire today?"

Pure local, no LLM. Single pass per tier.
"""
from __future__ import annotations

from typing import Any


def corpus_diff(
    *,
    agent: Any,
    since: float,
    n_episodes_scan: int = 5000,
    n_facts_scan: int = 5000,
) -> dict[str, Any]:
    """Compute the diff payload.

    Args:
      - `agent`: HippoAgent (or duck-type with `.semantic.list_facts`,
        `.memory.all`, `.skills.all`).
      - `since`: Unix timestamp; items with `created_at >= since`
        (or `updated_at >= since` for skills) are included.
      - `n_episodes_scan` / `n_facts_scan`: caps for the per-tier
        scan (defensive: don't try to materialise unbounded data).

    Returns: dict with keys
      `since`, `new_facts`, `new_episodes`, `updated_skills`,
      `outcome_breakdown`, `summary`.
    """
    semantic = getattr(agent, "semantic", None)
    memory = getattr(agent, "memory", None)
    skills_store = getattr(agent, "skills", None)

    new_facts: list[dict[str, Any]] = []
    if semantic is not None and hasattr(semantic, "list_facts"):
        try:
            for f in semantic.list_facts(limit=n_facts_scan, offset=0):
                ca = float(getattr(f, "created_at", 0.0))
                if ca >= since:
                    new_facts.append({
                        "id": getattr(f, "id", ""),
                        "proposition": getattr(f, "proposition", ""),
                        "topic": getattr(f, "topic", ""),
                        "created_at": ca,
                    })
        except Exception:
            new_facts = []

    new_episodes: list[dict[str, Any]] = []
    success_count = 0
    failure_count = 0
    if memory is not None and hasattr(memory, "all"):
        try:
            for ep in memory.all(limit=n_episodes_scan):
                ca = float(getattr(ep, "created_at", 0.0))
                if ca >= since:
                    outcome = getattr(ep, "outcome", "")
                    new_episodes.append({
                        "id": getattr(ep, "id", ""),
                        "task_text": (getattr(ep, "task_text", "") or "")[:200],
                        "outcome": outcome,
                        "created_at": ca,
                    })
                    if outcome == "success":
                        success_count += 1
                    elif outcome == "failure":
                        failure_count += 1
        except Exception:
            new_episodes = []

    updated_skills: list[dict[str, Any]] = []
    if skills_store is not None and hasattr(skills_store, "all"):
        try:
            for s in skills_store.all():
                ua = float(getattr(s, "updated_at", 0.0))
                if ua >= since:
                    updated_skills.append({
                        "id": getattr(s, "id", ""),
                        "name": getattr(s, "name", ""),
                        "status": getattr(s, "status", ""),
                        "trials": int(getattr(s, "trials", 0)),
                        "successes": int(getattr(s, "successes", 0)),
                        "fitness_mean": float(
                            getattr(s, "fitness_mean", 0.0)
                        ),
                        "updated_at": ua,
                    })
        except Exception:
            updated_skills = []

    summary = (
        f"Since {since}: "
        f"{len(new_facts)} new facts, "
        f"{len(new_episodes)} new episodes "
        f"({success_count} success, {failure_count} failure), "
        f"{len(updated_skills)} skills updated."
    )

    return {
        "since": since,
        "new_facts": new_facts,
        "new_episodes": new_episodes,
        "updated_skills": updated_skills,
        "outcome_breakdown": {
            "success": success_count,
            "failure": failure_count,
        },
        "summary": summary,
    }


__all__ = ["corpus_diff"]
