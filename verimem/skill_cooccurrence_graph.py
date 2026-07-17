"""R36: Skill co-occurrence graph.

Build full adjacency: nodes are skill ids that appear in any
episode.skills_used; edges are co-occurrence weights.

Useful for:
- visualizing skill clusters
- finding skills that bridge clusters (high betweenness)
- proposing super-skills from densely-connected sub-clusters
"""
from __future__ import annotations

from collections import defaultdict
from itertools import combinations
from typing import Any


def build_cooccurrence_graph(
    episodes: list[Any],
    *,
    top_k_edges: int = 200,
) -> dict[str, Any]:
    """Return graph as {nodes, edges} dict."""
    if not episodes:
        return {
            "nodes": [],
            "edges": [],
            "n_episodes_scanned": 0,
        }

    edge_weight: dict[tuple[str, str], int] = defaultdict(int)
    degree: dict[str, int] = defaultdict(int)
    appearances: dict[str, int] = defaultdict(int)

    for ep in episodes:
        skills = sorted(set(getattr(ep, "skills_used", []) or []))
        for s in skills:
            appearances[s] += 1
        for a, b in combinations(skills, 2):
            edge_weight[(a, b)] += 1
            degree[a] += 1
            degree[b] += 1

    nodes = [
        {"id": s, "degree": degree[s], "appearances": appearances[s]}
        for s in sorted(appearances.keys())
    ]

    edges = [
        {"from": a, "to": b, "weight": w}
        for (a, b), w in edge_weight.items()
    ]
    edges.sort(key=lambda e: -e["weight"])

    return {
        "nodes": nodes,
        "edges": edges[:top_k_edges],
        "n_episodes_scanned": len(episodes),
    }


__all__ = ["build_cooccurrence_graph"]
