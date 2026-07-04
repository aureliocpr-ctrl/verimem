"""R41: Recommend alternative skills after a failure.

Take a failed episode + the skills it used. Find OTHER skills whose
trigger matches the task BUT weren't used → candidates for next try.
"""
from __future__ import annotations

import re
from typing import Any

_TOKEN_RE = re.compile(r"[A-Za-z0-9_\-]+")


def _tokens(text: str) -> set[str]:
    return {t.lower() for t in _TOKEN_RE.findall(text or "")}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def recommend_alternatives(
    failed_episode: Any,
    *,
    skills: list[Any],
    min_match_score: float = 0.1,
    top_k: int = 10,
) -> dict[str, Any]:
    """Suggest skills similar to task but not already used."""
    task_tokens = _tokens(getattr(failed_episode, "task_text", ""))
    used = set(getattr(failed_episode, "skills_used", []) or [])

    scored: list[dict[str, Any]] = []
    for s in skills:
        sid = getattr(s, "id", "")
        if sid in used:
            continue
        if getattr(s, "status", "") == "retired":
            continue
        trig_tokens = _tokens(getattr(s, "trigger", ""))
        score = _jaccard(task_tokens, trig_tokens)
        if score < min_match_score:
            continue
        scored.append({
            "skill_id": sid,
            "match_score": round(score, 3),
            "trigger": getattr(s, "trigger", "")[:80],
        })

    scored.sort(key=lambda r: -r["match_score"])
    return {
        "recommendations": scored[:top_k],
        "n_skills_scanned": len(skills),
        "failed_episode_id": getattr(failed_episode, "id", ""),
    }


__all__ = ["recommend_alternatives"]
