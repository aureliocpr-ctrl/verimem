"""Cycle 189 (2026-05-23) — highway-node detector via sampled betweenness.

Closes gap §6.1 of docs/sota/highway-nodes-pagerank-cache.md
(cycle 188). Pure function that returns the top-K fact ids with
highest betweenness centrality — i.e. facts that bridge otherwise-
disjoint Louvain communities (cycle 186).

Composes-over
-------------
* ``verimem.community_detector._load_graph`` — reuses the same node +
  edge build path so highway detection sees the same alive-only
  subgraph as community detection. Imported via the lower-level
  module rather than via ``detect_communities`` to avoid pulling the
  full Louvain solver when only the graph is needed.

Algorithm
---------
``networkx.betweenness_centrality(g, k=sample_size)`` — sampled
betweenness in O(k · (N+M)). Full betweenness is O(N³) which would
not scale past a few thousand nodes; sampling is the standard SOTA
trade-off (Brandes 2001 sampling variant).

Defensive
---------
* Missing DB / SQL error / empty graph → ``[]``, never raises.
* Single-node graph → ``[(id, 0.0)]``.
* Disconnected graph: betweenness computed per-component; the global
  ranking still makes sense (bridge of largest component ranks high).
"""
from __future__ import annotations

from pathlib import Path

import networkx as nx

from verimem.community_detector import _load_graph

_DEFAULT_SAMPLE_SIZE: int = 500


def get_highway_nodes(
    semantic_db: Path | str,
    *,
    k: int = 50,
    sample_size: int = _DEFAULT_SAMPLE_SIZE,
    edges_source: str = "both",
    seed: int = 42,
) -> list[tuple[str, float]]:
    """Return up to ``k`` highway fact ids sorted by betweenness DESC.

    Args:
        semantic_db: path to ``semantic.db``.
        k: cap on returned list length.
        sample_size: number of pivots for sampled betweenness; clamped
            internally so we never sample more nodes than the graph has.
        edges_source: ``"lineage"`` / ``"causal"`` / ``"both"``
            (forwarded to ``_load_graph``).
        seed: RNG seed for sampling determinism.

    Returns:
        ``[(fact_id, betweenness_score), ...]`` length ≤ ``k``.
        Empty list on missing DB / empty graph / error path.
    """
    p = Path(semantic_db)
    if not p.exists():
        return []
    try:
        g = _load_graph(p, edges_source)  # type: ignore[arg-type]
    except Exception:
        return []
    n = g.number_of_nodes()
    if n == 0:
        return []
    # Clamp sample_size to graph size; networkx errors when k > N.
    eff_k = min(int(sample_size), n)
    try:
        if eff_k < n:
            scores = nx.betweenness_centrality(
                g, k=eff_k, seed=int(seed),
            )
        else:
            # Sampling with k=N is equivalent to full computation; skip
            # the random sampling overhead by calling without k.
            scores = nx.betweenness_centrality(g)
    except Exception:
        return []
    ranked: list[tuple[str, float]] = sorted(
        scores.items(), key=lambda kv: -float(kv[1]),
    )
    return [(str(node_id), float(score)) for node_id, score in ranked[: int(k)]]


__all__ = ["get_highway_nodes"]
