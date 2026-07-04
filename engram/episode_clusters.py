"""Episode clustering by task_text token Jaccard.

FORGIA pezzo #226 — Wave 25. No embeddings — pure string token
overlap. Greedy single-link clustering.

Useful for:
  - "quali task ho già fatto?" (dedup near-misses)
  - finding the cluster the current task belongs to
  - skill-compilation candidates (episodes in same cluster)
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


def cluster_episodes(
    episodes: list[Any],
    *,
    threshold: float = 0.5,
    top_k: int = 50,
) -> dict[str, Any]:
    """Greedy single-link clustering of episodes by task_text Jaccard.

    Args:
      - `episodes`: iterable of episode-likes with `id` and
        `task_text`.
      - `threshold`: minimum Jaccard to join a cluster. Default 0.5.
      - `top_k`: cap on returned clusters (sorted by size DESC).

    Returns: `{n_episodes, threshold, clusters}` where each cluster
    is `{members, size, sample_text}`.
    """
    eps = list(episodes)
    n = len(eps)
    if n == 0:
        return {"n_episodes": 0, "threshold": threshold, "clusters": []}

    sigs = [_tokens(getattr(ep, "task_text", "")) for ep in eps]
    visited = [False] * n
    clusters: list[dict[str, Any]] = []

    for i in range(n):
        if visited[i]:
            continue
        members = [eps[i].id]
        sample = (getattr(eps[i], "task_text", "") or "")[:160]
        visited[i] = True
        for j in range(i + 1, n):
            if visited[j]:
                continue
            if _jaccard(sigs[i], sigs[j]) >= threshold:
                visited[j] = True
                members.append(eps[j].id)
        clusters.append({
            "members": members,
            "size": len(members),
            "sample_text": sample,
        })

    clusters.sort(key=lambda c: -c["size"])
    return {
        "n_episodes": n,
        "threshold": threshold,
        "clusters": clusters[:top_k],
    }


__all__ = ["cluster_episodes"]
