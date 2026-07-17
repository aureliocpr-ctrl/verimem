"""R38: Cluster failed episodes by task signature.

Focused subset of episode clustering — only failures. For each
cluster, also aggregate common tokens in final_answer (probable
error pattern).
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from typing import Any

_TOKEN_RE = re.compile(r"[A-Za-z0-9_\-]+")
_STOP = frozenset({
    "the", "a", "an", "and", "or", "of", "to", "for", "in", "on",
    "at", "by", "with", "is", "was", "were", "be", "been", "has",
    "have", "had", "do", "does", "did", "this", "that", "it",
    "error", "fail", "failed", "failure",
})


def _signature(text: str, n: int = 5) -> str:
    toks = [t.lower() for t in _TOKEN_RE.findall(text or "")]
    counter = Counter(toks)
    return ",".join(sorted(t for t, _ in counter.most_common(n)))


def _informative_tokens(text: str) -> list[str]:
    return [
        t.lower() for t in _TOKEN_RE.findall(text or "")
        if t.lower() not in _STOP and len(t) > 2
    ]


def cluster_failures(
    episodes: list[Any],
    *,
    min_cluster_size: int = 2,
    top_k: int = 50,
) -> dict[str, Any]:
    """Group failures by task signature + extract common error tokens."""
    failures = [
        e for e in episodes if getattr(e, "outcome", "") == "failure"
    ]
    if not failures:
        return {"clusters": [], "n_failures_scanned": 0}

    buckets: dict[str, list[Any]] = defaultdict(list)
    for e in failures:
        sig = _signature(getattr(e, "task_text", ""))
        buckets[sig].append(e)

    clusters: list[dict[str, Any]] = []
    for sig, group in buckets.items():
        if len(group) < min_cluster_size:
            continue
        # Common tokens across final_answers
        token_counter: Counter[str] = Counter()
        for e in group:
            token_counter.update(_informative_tokens(
                getattr(e, "final_answer", "")
            ))
        common = [{"token": t, "count": c}
                  for t, c in token_counter.most_common(5)]
        clusters.append({
            "signature": sig,
            "n_failures": len(group),
            "episode_ids": [getattr(e, "id", "") for e in group[:10]],
            "common_error_tokens": common,
        })

    clusters.sort(key=lambda c: -c["n_failures"])
    return {
        "clusters": clusters[:top_k],
        "n_failures_scanned": len(failures),
    }


__all__ = ["cluster_failures"]
