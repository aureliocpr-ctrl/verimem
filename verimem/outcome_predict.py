"""Rule-based outcome prediction.

FORGIA pezzo #252 — Wave 51. Before executing a task, estimate
probability of success based on similar past episodes (Jaccard on
task_text tokens). Pure local.

`confidence` = min(n_similar / 5, 1.0) — more matches => more
confident in the estimate. With 0 matches, confidence is 0 and
p_success/p_failure default to 0.5 (uninformed prior).
"""
from __future__ import annotations

import re
from typing import Any

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> set[str]:
    return set(_TOKEN_RE.findall((text or "").lower()))


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    union = len(a | b)
    return len(a & b) / union if union > 0 else 0.0


def predict_outcome(
    *,
    task: str,
    episodes: list[Any],
    threshold: float = 0.3,
    top_k: int = 10,
) -> dict[str, Any]:
    """Estimate p(success) for `task` from similar past episodes.

    Args:
      - `task`: new task to predict.
      - `episodes`: past episodes (with task_text + outcome).
      - `threshold`: minimum Jaccard to count as similar.
      - `top_k`: cap on returned similar episodes.

    Returns: `{task, n_similar, p_success, p_failure, confidence,
    similar_episodes}`.
    """
    sig = _tokens(task)
    matches: list[tuple[Any, float]] = []
    for ep in episodes:
        j = _jaccard(sig, _tokens(getattr(ep, "task_text", "")))
        if j >= threshold:
            matches.append((ep, j))
    matches.sort(key=lambda x: -x[1])

    n = len(matches)
    n_succ = sum(
        1 for ep, _ in matches
        if getattr(ep, "outcome", "") == "success"
    )
    n_fail = sum(
        1 for ep, _ in matches
        if getattr(ep, "outcome", "") == "failure"
    )

    if n == 0:
        p_success = 0.5
        p_failure = 0.5
        confidence = 0.0
    else:
        # Laplace smoothing (1, 1) to avoid 0/1 extremes.
        p_success = (n_succ + 1) / (n_succ + n_fail + 2)
        p_failure = 1.0 - p_success
        confidence = min(n / 5.0, 1.0)

    similar_records = [
        {
            "task_text": (getattr(ep, "task_text", "") or "")[:160],
            "outcome": getattr(ep, "outcome", ""),
            "jaccard": float(j),
        }
        for ep, j in matches[:top_k]
    ]

    return {
        "task": task,
        "n_similar": n,
        "p_success": float(p_success),
        "p_failure": float(p_failure),
        "confidence": float(confidence),
        "similar_episodes": similar_records,
    }


__all__ = ["predict_outcome"]
