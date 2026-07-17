r"""Cycle 261 (2026-05-23) — Partition Stabilization: REAL SOS mitigation.

The cycle 253-260 second-pass Louvain was empirically found (cycle 260
critic-gate disclosure) to NOT reduce the observer-shift partition
effect. It enhances detection by revealing latent candidates, but
re-running Louvain on a self-modified graph still produces a Jaccard
distance > 0 from the prior partition.

This module implements the REAL mitigation: persistent partition
assignments. Given a prior partition $P_{t_0}$, we force unchanged
nodes to inherit their $P_{t_0}$ assignment, and only assign NEW
(injected) nodes via a local-move heuristic (assign to the community
of the new node's most strongly connected neighbor).

By construction, this guarantees:
    $\Delta_J(P_{t_0}, P_{t_1})$ over unchanged nodes = 0.0

New nodes contribute to the Jaccard only via their pair-relationships
with existing nodes, which are deterministically inherited from the
neighbor's community.

A4 honest tradeoff:
    The resulting partition is NOT global-modularity-optimal at t1.
    It is a stable, monotonically-growing partition. For applications
    that require partition stability under writes (skill emergence
    pipeline), this is the correct tradeoff. For applications that
    require fresh discovery (community evolution analysis), Louvain
    rerun is correct.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import networkx as nx

from verimem.community_detector import _load_graph


@dataclass
class Partition:
    """A community partition: node-id → community-id mapping.

    Persistent partition that can be extended with new nodes without
    re-assigning existing ones.
    """
    node_to_community: dict[str, str] = field(default_factory=dict)

    def values_as_sets(self) -> list[set[str]]:
        """Group nodes by community → list of node-id sets."""
        groups: dict[str, set[str]] = defaultdict(set)
        for n, c in self.node_to_community.items():
            groups[c].add(n)
        return list(groups.values())

    def community_of(self, node: str) -> str | None:
        return self.node_to_community.get(node)


def _louvain_fresh(graph: nx.Graph, seed: int) -> Partition:
    """Run vanilla Louvain on graph, return Partition."""
    if graph.number_of_nodes() == 0:
        return Partition()
    try:
        comms = nx.algorithms.community.louvain_communities(
            graph, weight="weight", seed=int(seed),
        )
    except Exception:  # noqa: BLE001
        return Partition()
    mapping: dict[str, str] = {}
    for i, c in enumerate(comms):
        cid = f"c-{i:03d}"
        for n in c:
            mapping[str(n)] = cid
    return Partition(node_to_community=mapping)


def _extend_with_new_nodes(
    prior: Partition,
    graph: nx.Graph,
    new_nodes: set[str],
) -> Partition:
    """For each new node, assign it to the community of its highest-weight
    neighbor that is already assigned. Fallback: singleton community.
    """
    extended = dict(prior.node_to_community)
    fresh_singleton_idx = 0

    # Deterministic order (sorted) — for reproducibility
    for n in sorted(new_nodes):
        # Find most strongly connected assigned neighbor
        best_community: str | None = None
        best_weight = -1.0
        if n in graph:
            for nbr in graph.neighbors(n):
                nbr_s = str(nbr)
                if nbr_s in extended:
                    w = float(graph[n][nbr].get("weight", 1.0))
                    if w > best_weight:
                        best_weight = w
                        best_community = extended[nbr_s]
        if best_community is None:
            best_community = f"fresh-{fresh_singleton_idx:03d}"
            fresh_singleton_idx += 1
        extended[n] = best_community

    return Partition(node_to_community=extended)


def stable_partition(
    semantic_db: Path | str,
    *,
    seed: int = 42,
    prior_assignment: Partition | None = None,
    edges_source: str = "both",
) -> Partition:
    """Compute a stable partition over the semantic graph.

    Args:
        semantic_db: path to ``semantic.db``.
        seed: Louvain seed for the fresh-from-scratch case.
        prior_assignment: optional Partition to inherit from. When
            given, unchanged nodes preserve their assignment; only
            new nodes get a fresh assignment.
        edges_source: ``"lineage" | "causal" | "both"``.

    Returns:
        Partition object.

    Defensive:
        Missing DB / empty graph → empty Partition.
    """
    p = Path(semantic_db)
    if not p.exists():
        return Partition()

    try:
        g = _load_graph(p, edges_source)  # type: ignore[arg-type]
    except Exception:  # noqa: BLE001
        return Partition()

    if g.number_of_nodes() == 0:
        return Partition()

    current_nodes = {str(n) for n in g.nodes()}

    if prior_assignment is None or not prior_assignment.node_to_community:
        # No prior — fresh Louvain.
        return _louvain_fresh(g, seed=seed)

    prior_nodes = set(prior_assignment.node_to_community)
    new_nodes = current_nodes - prior_nodes
    # missing_nodes (in prior but not current) are dropped silently
    # (e.g. superseded facts). Future work: explicit deletion handling.

    if not new_nodes:
        # No new nodes → inherit unchanged
        return Partition(
            node_to_community={
                n: prior_assignment.node_to_community[n]
                for n in current_nodes
                if n in prior_assignment.node_to_community
            },
        )

    return _extend_with_new_nodes(prior_assignment, g, new_nodes)


def partition_jaccard(
    p1: Partition,
    p2: Partition,
    *,
    restrict_to: set[str] | None = None,
) -> float:
    """Jaccard distance between two partitions over node-pair
    co-clustering.

    Args:
        restrict_to: when given, only consider node pairs where both
            endpoints are in this set. Used to isolate the
            unchanged-node measurement.

    Returns:
        1 - |co-clustered both| / |co-clustered either|. Returns 0.0
        when both partitions agree on all considered pairs.
    """
    def co_pairs(p: Partition, allowed: set[str] | None) -> set[frozenset[str]]:
        out: set[frozenset[str]] = set()
        groups = p.values_as_sets()
        for c in groups:
            members = sorted(c) if allowed is None else sorted(c & allowed)
            for i in range(len(members)):
                for j in range(i + 1, len(members)):
                    out.add(frozenset({members[i], members[j]}))
        return out

    pairs_1 = co_pairs(p1, restrict_to)
    pairs_2 = co_pairs(p2, restrict_to)
    inter = pairs_1 & pairs_2
    union = pairs_1 | pairs_2
    if not union:
        return 0.0
    return 1.0 - (len(inter) / len(union))


__all__ = [
    "Partition",
    "partition_jaccard",
    "stable_partition",
]
