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

    # ⚖️ Le due basi del confronto. Senza, «correlated with success» non e'
    #    leggibile: su un corpus con 8 fallimenti su 459 (misurato il 30/08 al
    #    tool MCP) i negativi sono impossibili per costruzione e i positivi
    #    stanno tutti a 1.0 — cioe' sono i token piu' FREQUENTI, non quelli
    #    correlati. Chi legge deve poterlo vedere senza contare gli episodi.
    #    Gli esiti diversi da success/failure non entrano in nessuno dei due:
    #    «non e' un successo» non vuol dire «e' un fallimento».
    n_success = n_failure = 0

    for ep in episodes:
        outcome = getattr(ep, "outcome", "")
        if outcome == "success":
            n_success += 1
        elif outcome == "failure":
            n_failure += 1
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
        "n_success": n_success,
        "n_failure": n_failure,
    }


__all__ = ["find_outcome_patterns"]
