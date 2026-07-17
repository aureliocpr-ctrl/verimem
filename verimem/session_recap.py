"""End-of-session activity recap.

FORGIA pezzo #261 — Wave 60. Summary of all activity since a
session-start timestamp: episodes/facts/skills touched, top
skills, total tokens, outcome breakdown, summary string.
"""
from __future__ import annotations

from collections import Counter
from typing import Any


def session_recap(
    *,
    since: float,
    agent: Any,
    top_k_skills: int = 5,
) -> dict[str, Any]:
    """Recap session activity since `since` (Unix timestamp)."""
    n_episodes = 0
    n_success = 0
    n_failure = 0
    total_tokens = 0
    skill_counts: Counter[str] = Counter()
    try:
        for ep in agent.memory.all():
            ts = float(getattr(ep, "created_at", 0.0) or 0.0)
            if ts < since:
                continue
            n_episodes += 1
            outcome = getattr(ep, "outcome", "")
            if outcome == "success":
                n_success += 1
            elif outcome == "failure":
                n_failure += 1
            total_tokens += int(getattr(ep, "tokens_used", 0) or 0)
            for s in (getattr(ep, "skills_used", []) or []):
                skill_counts[s] += 1
    except Exception:
        pass

    n_facts_added = 0
    try:
        for f in agent.semantic.list_facts(limit=10000, offset=0):
            ts = float(getattr(f, "created_at", 0.0) or 0.0)
            if ts >= since:
                n_facts_added += 1
    except Exception:
        pass

    top_skills_used = [
        {"skill_id": s, "count": c}
        for s, c in skill_counts.most_common(top_k_skills)
    ]

    summary = (
        f"Session since {since}: {n_episodes} ep "
        f"({n_success}✓/{n_failure}✗), "
        f"{n_facts_added} new facts, "
        f"{total_tokens} tokens, "
        f"{len(skill_counts)} unique skills used."
    )

    return {
        "since": since,
        "n_episodes": n_episodes,
        "n_success": n_success,
        "n_failure": n_failure,
        "n_facts_added": n_facts_added,
        "total_tokens": total_tokens,
        "top_skills_used": top_skills_used,
        "summary": summary,
    }


__all__ = ["session_recap"]
