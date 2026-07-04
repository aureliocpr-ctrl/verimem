"""R24: Skill warmup — predict which skills should be preloaded.

Given upcoming tasks, score each skill by aggregate match across
all upcoming tasks. Highest-aggregate skills are best candidates
for keeping warm.

Score(skill) = sum_over_tasks(jaccard(skill.trigger, task))
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


def predict_warmup_skills(
    *,
    upcoming_tasks: list[str],
    skills: list[Any],
    min_score: float = 0.05,
    top_k: int = 20,
) -> dict[str, Any]:
    """Rank skills by aggregate match to upcoming tasks."""
    if not upcoming_tasks or not skills:
        return {
            "warmup": [],
            "n_skills_scanned": len(skills),
            "n_tasks": len(upcoming_tasks),
        }

    task_token_sets = [_tokens(t) for t in upcoming_tasks]

    scored: list[dict[str, Any]] = []
    for s in skills:
        if getattr(s, "status", "") == "retired":
            continue
        trig_tokens = _tokens(getattr(s, "trigger", ""))
        if not trig_tokens:
            continue
        total = sum(_jaccard(trig_tokens, t) for t in task_token_sets)
        if total < min_score:
            continue
        scored.append({
            "skill_id": getattr(s, "id", ""),
            "name": getattr(s, "name", "") if hasattr(s, "name") else "",
            "score": round(total, 3),
            "trigger": getattr(s, "trigger", "")[:80],
        })

    scored.sort(key=lambda x: -x["score"])
    return {
        "warmup": scored[:top_k],
        "n_skills_scanned": len(skills),
        "n_tasks": len(upcoming_tasks),
    }


__all__ = ["predict_warmup_skills"]
