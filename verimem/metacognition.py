"""R3: Metacognition — calibrated confidence on recall results.

HippoAgent knows when it knows, and knows when it doesn't.

Given the output of `hippo_recall` (list of {similarity, outcome, ...})
this module returns a structured confidence verdict:

  - "high"   : strong match (max sim ≥0.7) + ≥3 episodes + outcome
               agreement ≥66%
  - "medium" : decent match (max sim ≥0.5)
  - "low"    : weak match (max sim ≥0.3)
  - "none"   : irrelevant or empty (max sim <0.3)

The "score" is a normalized 0..1 number combining max similarity and
outcome agreement, useful for sorting fallback strategies.

Use case: before answering a factual question or starting a new task,
call assess_recall_confidence on the recall result. If level == "none"
or "low", trigger fallback (ask user, search externally).
"""
from __future__ import annotations

from collections import Counter
from typing import Any

_FALLBACKS = {
    "high": "memory is solid — proceed with confidence",
    "medium": "memory partially relevant — proceed but verify key facts",
    "low": "memory is weak — verify externally before relying on it",
    "none": "no relevant memory — ask the user, or search externally",
}


def assess_recall_confidence(
    recall_results: list[dict[str, Any]],
    *,
    high_sim_threshold: float = 0.7,
    medium_sim_threshold: float = 0.5,
    low_sim_threshold: float = 0.3,
    min_episodes_for_high: int = 3,
    outcome_agreement_for_high: float = 0.75,
) -> dict[str, Any]:
    """Score how trustworthy a recall result is."""
    if not recall_results:
        return {
            "level": "none",
            "score": 0.0,
            "max_similarity": 0.0,
            "n_episodes": 0,
            "outcome_agreement": 0.0,
            "fallback_suggestion": _FALLBACKS["none"],
        }

    sims = [float(r.get("similarity", 0.0)) for r in recall_results]
    max_sim = max(sims) if sims else 0.0
    n_eps = len(recall_results)

    # Outcome agreement = majority outcome share among top-k
    outcomes = [r.get("outcome", "") for r in recall_results]
    counter = Counter(outcomes)
    if counter:
        top_outcome, top_count = counter.most_common(1)[0]
        outcome_agreement = top_count / n_eps
    else:
        outcome_agreement = 0.0

    # Level derivation
    level: str
    if max_sim < low_sim_threshold:
        level = "none"
    elif max_sim < medium_sim_threshold:
        level = "low"
    elif max_sim < high_sim_threshold:
        level = "medium"
    else:
        # max_sim >= high threshold — but require both criteria for "high"
        if (n_eps >= min_episodes_for_high
                and outcome_agreement >= outcome_agreement_for_high):
            level = "high"
        else:
            # Sim is high but corpus too thin or split → medium
            level = "medium"

    # Score: convex combo of max_sim and outcome_agreement (weighted)
    score = round(0.7 * max_sim + 0.3 * outcome_agreement, 3)

    return {
        "level": level,
        "score": score,
        "max_similarity": round(max_sim, 3),
        "n_episodes": n_eps,
        "outcome_agreement": round(outcome_agreement, 3),
        "fallback_suggestion": _FALLBACKS[level],
    }


__all__ = ["assess_recall_confidence"]
