"""R33: Memory health report.

Compose a single 0-100 health score from:
  - episodes: success_rate weight 40%
  - skills: promoted_ratio weight 35%
  - facts: avg_confidence weight 25%

Verdict thresholds: >=80 Healthy, >=60 Acceptable, >=40 Needs
attention, >=1 Poor, 0 Empty.

Returns recommendations list (text) for low-scoring components.
"""
from __future__ import annotations

import time
from typing import Any


def _episodes_score(episodes: list[Any]) -> float:
    if not episodes:
        return 0.0
    succ = sum(1 for e in episodes if getattr(e, "outcome", "") == "success")
    return (succ / len(episodes)) * 100.0


def _skills_score(skills: list[Any]) -> float:
    if not skills:
        return 0.0
    promoted = sum(1 for s in skills if getattr(s, "status", "") == "promoted")
    retired = sum(1 for s in skills if getattr(s, "status", "") == "retired")
    active = len(skills) - retired
    if active <= 0:
        return 0.0
    return (promoted / active) * 100.0


def _facts_score(facts: list[Any]) -> float:
    if not facts:
        return 0.0
    confs = [
        float(getattr(f, "confidence", 0.0) or 0.0) for f in facts
    ]
    return (sum(confs) / len(confs)) * 100.0 if confs else 0.0


def generate_health_report(
    *,
    episodes: list[Any],
    skills: list[Any],
    facts: list[Any],
    now: float | None = None,
) -> dict[str, Any]:
    """Composite health metric + breakdown + recommendations."""
    if now is None:
        now = time.time()
    ep_score = _episodes_score(episodes)
    sk_score = _skills_score(skills)
    f_score = _facts_score(facts)

    overall = round(0.40 * ep_score + 0.35 * sk_score + 0.25 * f_score, 1)

    if not episodes and not skills and not facts:
        verdict = "Empty"
    elif overall >= 80:
        verdict = "Healthy"
    elif overall >= 60:
        verdict = "Acceptable"
    elif overall >= 40:
        verdict = "Needs attention"
    else:
        verdict = "Poor"

    recommendations: list[str] = []
    if ep_score < 50 and episodes:
        recommendations.append(
            f"Episode success rate is {ep_score:.0f}%: investigate "
            "frequent failure patterns (hippo_diagnose_failure)."
        )
    if sk_score < 30 and skills:
        recommendations.append(
            f"Promoted ratio is {sk_score:.0f}%: many candidates "
            "waiting — run consolidation or hippo_skill_bottlenecks."
        )
    if f_score < 50 and facts:
        recommendations.append(
            f"Avg fact confidence is {f_score:.0f}%: low-trust pool. "
            "Use hippo_rank_facts_trust to prune."
        )
    if not recommendations:
        recommendations.append("Memory is in good shape.")

    return {
        "overall_score": int(overall),
        "verdict": verdict,
        "components": {
            "episodes_score": round(ep_score, 1),
            "skills_score": round(sk_score, 1),
            "facts_score": round(f_score, 1),
        },
        "counts": {
            "n_episodes": len(episodes),
            "n_skills": len(skills),
            "n_facts": len(facts),
        },
        "recommendations": recommendations,
    }


__all__ = ["generate_health_report"]
