"""R42: Outcome pattern finder.

For each informative token in task_text, compute success_rate when
that token is present. Tokens above/below thresholds become
positive/negative signals.

Stopwords excluded.
"""
from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

_TOKEN_RE = re.compile(r"[A-Za-z0-9_\-]+")
_STOP = frozenset({
    "the", "a", "an", "and", "or", "of", "to", "for", "in", "on",
    "at", "by", "with", "is", "was", "were", "be", "been",
    "has", "have", "had", "do", "does", "did", "this", "that",
})


def _tokens(text: str) -> list[str]:
    return [
        t.lower() for t in _TOKEN_RE.findall(text or "")
        if t.lower() not in _STOP and len(t) > 2
    ]


def find_outcome_patterns(
    episodes: list[Any],
    *,
    min_occurrence: int = 3,
    positive_threshold: float = 0.7,
    negative_threshold: float = 0.3,
    top_k: int = 30,
) -> dict[str, Any]:
    """Find tokens correlated with success/failure."""
    occurrences: dict[str, int] = defaultdict(int)
    successes: dict[str, int] = defaultdict(int)

    for ep in episodes:
        outcome = getattr(ep, "outcome", "")
        for tok in set(_tokens(getattr(ep, "task_text", ""))):
            occurrences[tok] += 1
            if outcome == "success":
                successes[tok] += 1

    pos: list[dict[str, Any]] = []
    neg: list[dict[str, Any]] = []
    for tok, n_occ in occurrences.items():
        if n_occ < min_occurrence:
            continue
        rate = successes[tok] / n_occ
        entry = {
            "token": tok,
            "n_occurrences": n_occ,
            "success_rate": round(rate, 3),
        }
        if rate >= positive_threshold:
            pos.append(entry)
        elif rate <= negative_threshold:
            neg.append(entry)

    pos.sort(key=lambda e: (-e["success_rate"], -e["n_occurrences"]))
    neg.sort(key=lambda e: (e["success_rate"], -e["n_occurrences"]))

    return {
        "positive_signals": pos[:top_k],
        "negative_signals": neg[:top_k],
        "n_episodes_scanned": len(episodes),
    }


__all__ = ["find_outcome_patterns"]
