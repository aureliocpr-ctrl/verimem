"""R23: Failure diagnosis — root cause from similar past failures.

Given a failed target episode, find past failures with similar
task_text, then extract the most frequent informative token from
their final_answer fields. That's the candidate root cause.

Confidence levels based on # similar + token concentration.
"""
from __future__ import annotations

import re
from collections import Counter
from typing import Any

_TOKEN_RE = re.compile(r"[A-Za-z0-9_\-]+")
# Trivial stopwords for failure analysis
_STOP = frozenset({
    "the", "a", "an", "and", "or", "of", "to", "for", "in", "on",
    "at", "by", "with", "is", "was", "were", "be", "been", "has",
    "have", "had", "do", "does", "did", "will", "would", "could",
    "this", "that", "it", "its", "as", "but", "not", "no", "yes",
    "from", "into", "out", "up", "down", "over", "under", "again",
    "error", "fail", "failed", "failure",  # too generic in failure context
})


def _tokens(text: str) -> set[str]:
    return {
        t.lower() for t in _TOKEN_RE.findall(text or "")
        if t.lower() not in _STOP and len(t) > 2
    }


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def diagnose_failure(
    target: Any,
    *,
    past_episodes: list[Any],
    task_similarity_threshold: float = 0.2,
    top_k: int = 10,
) -> dict[str, Any]:
    """Find the dominant failure pattern across similar past failures."""
    target_tokens = _tokens(getattr(target, "task_text", ""))

    # Filter: past failures only, similar task
    similar: list[Any] = []
    for ep in past_episodes:
        if getattr(ep, "outcome", "") != "failure":
            continue
        ep_tokens = _tokens(getattr(ep, "task_text", ""))
        if _jaccard(target_tokens, ep_tokens) >= task_similarity_threshold:
            similar.append(ep)

    if not similar:
        return {
            "root_cause": "",
            "confidence": "none",
            "n_similar_failures": 0,
            "similar_ids": [],
        }

    # Aggregate informative tokens from final_answer
    counter: Counter[str] = Counter()
    for ep in similar:
        ans_tokens = _tokens(getattr(ep, "final_answer", ""))
        counter.update(ans_tokens)

    if not counter:
        return {
            "root_cause": "",
            "confidence": "low",
            "n_similar_failures": len(similar),
            "similar_ids": [getattr(e, "id", "") for e in similar[:top_k]],
        }

    top = counter.most_common(3)
    root_cause_tokens = [t for t, _ in top]
    root_cause = " / ".join(root_cause_tokens)

    # Confidence: based on # similar + concentration
    n = len(similar)
    top_freq = top[0][1] / max(1, len(similar))
    if n >= 3 and top_freq >= 0.6:
        confidence = "high"
    elif n >= 2 and top_freq >= 0.4:
        confidence = "medium"
    elif n >= 1:
        confidence = "low"
    else:
        confidence = "none"

    return {
        "root_cause": root_cause,
        "confidence": confidence,
        "n_similar_failures": n,
        "similar_ids": [getattr(e, "id", "") for e in similar[:top_k]],
        "top_tokens": [{"token": t, "count": c} for t, c in top],
    }


__all__ = ["diagnose_failure"]
