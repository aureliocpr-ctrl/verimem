"""Top failing skills batch.

FORGIA pezzo #266 — Wave 65. Aggregates failures per skill,
returns top N. Useful for triage.
"""
from __future__ import annotations

from collections import Counter
from typing import Any

from .skill import Skill


def top_failing_skills(
    *,
    skills: list[Skill],
    episodes: list[Any],
    top_k: int = 20,
) -> dict[str, Any]:
    """Return skills with the most failures."""
    skill_ids = {s.id for s in skills}
    fail_counts: Counter[str] = Counter()
    total_counts: Counter[str] = Counter()
    for ep in episodes:
        used = set(getattr(ep, "skills_used", None) or [])
        outcome = getattr(ep, "outcome", "")
        for sid in used:
            if sid not in skill_ids:
                continue
            total_counts[sid] += 1
            if outcome == "failure":
                fail_counts[sid] += 1

    records: list[dict[str, Any]] = []
    for sid, n_fail in fail_counts.most_common(top_k):
        n_total = total_counts[sid]
        records.append({
            "skill_id": sid,
            "n_failures": n_fail,
            "n_total_uses": n_total,
            "failure_rate": n_fail / n_total if n_total > 0 else 0.0,
        })
    return {"skills": records, "n_total_skills_with_failures": len(fail_counts)}


__all__ = ["top_failing_skills"]
