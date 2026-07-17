"""Cycle #85 — topic cleanup suggestions.

P5 fix from cycle 2026-05-16 stress-test + cycle #84 empirical
finding: 86/836 = 10.3% of Aurelio's facts have empty topic. They
pollute recall and break the project/<name>/* convention.

For each orphan fact, find the k nearest neighbours among the
live-topic-bearing facts (cosine on embedding). The most-voted
topic among those neighbours becomes the suggestion. Pure-local.
"""
from __future__ import annotations

from collections import Counter
from typing import Any

import numpy as np

from . import embedding
from .semantic import SemanticMemory


def _cosine_matrix(query: np.ndarray, corpus: np.ndarray) -> np.ndarray:
    """Compute cosine similarity between a query vector and every row
    of corpus. Returns 1-D array of length corpus.shape[0]."""
    qn = float(np.linalg.norm(query))
    if qn == 0.0:
        return np.zeros(corpus.shape[0], dtype=np.float32)
    cn = np.linalg.norm(corpus, axis=1)
    cn[cn == 0] = 1.0
    sims = (corpus @ query) / (cn * qn)
    return sims


def topic_cleanup_suggestions(
    semantic: SemanticMemory, *,
    max_suggestions: int = 20,
    sim_threshold: float = 0.6,
    k_neighbours: int = 5,
) -> dict[str, Any]:
    """Suggest a topic for each orphan fact (empty/None topic).

    Args:
        semantic: SemanticMemory instance.
        max_suggestions: cap on the returned ``suggestions`` list.
        sim_threshold: minimum cosine similarity for the nearest
            neighbour. If the best neighbour is below this, the
            orphan is skipped (truly off-cluster).
        k_neighbours: number of nearest live-topic facts inspected
            per orphan. The topic with the most votes wins. Ties
            are broken by highest similarity.

    Returns:
        dict ``{n_facts_no_topic, suggestions}``.
    """
    with semantic._connect() as conn:
        orphan_rows = conn.execute(
            "SELECT id, proposition, embedding FROM facts "
            "WHERE (topic = '' OR topic IS NULL) "
            "AND superseded_by IS NULL",
        ).fetchall()
        live_rows = conn.execute(
            "SELECT id, topic, proposition, embedding FROM facts "
            "WHERE topic != '' AND topic IS NOT NULL "
            "AND superseded_by IS NULL",
        ).fetchall()

    n_orphans = len(orphan_rows)
    if not orphan_rows or not live_rows:
        return {"n_facts_no_topic": n_orphans, "suggestions": []}

    # Build live-topic matrix once.
    try:
        live_embs = np.stack([
            embedding.deserialize(r["embedding"]) for r in live_rows
        ])
    except Exception:
        return {"n_facts_no_topic": n_orphans, "suggestions": []}

    suggestions: list[dict[str, Any]] = []
    for orow in orphan_rows:
        try:
            q = embedding.deserialize(orow["embedding"])
        except Exception:
            continue
        sims = _cosine_matrix(q, live_embs)
        # Top-k neighbours by similarity
        top_idx = np.argsort(-sims)[:max(1, int(k_neighbours))]
        # Filter under threshold
        good = [(int(i), float(sims[i])) for i in top_idx if sims[i] >= sim_threshold]
        if not good:
            continue
        # Vote on topic with tie-break on best similarity
        votes: Counter[str] = Counter()
        best_sim_per_topic: dict[str, float] = {}
        for i, sim in good:
            topic = live_rows[i]["topic"]
            votes[topic] += 1
            best_sim_per_topic[topic] = max(
                best_sim_per_topic.get(topic, -1.0), sim,
            )
        # Pick top topic — ties broken by best similarity
        sorted_topics = sorted(
            votes.items(),
            key=lambda kv: (-kv[1], -best_sim_per_topic.get(kv[0], 0.0)),
        )
        best_topic, vote_count = sorted_topics[0]
        suggestions.append({
            "fact_id": orow["id"],
            "proposition": (orow["proposition"] or "")[:120],
            "suggested_topic": best_topic,
            "similarity": best_sim_per_topic[best_topic],
            "votes": vote_count,
        })
        if len(suggestions) >= max_suggestions:
            break

    # Sort suggestions by similarity DESC for actionability
    suggestions.sort(key=lambda s: -s["similarity"])
    return {
        "n_facts_no_topic": n_orphans,
        "suggestions": suggestions[:max_suggestions],
    }


__all__ = ["topic_cleanup_suggestions"]
