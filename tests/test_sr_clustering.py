"""Tests for FORGIA pezzo #23: SR-based skill clustering.

The existing SkillLibrary clustering uses cosine over trigger
embeddings — "skills with similar names". The Successor Representation
(pezzo #20) gives an orthogonal signal: "skills with similar future
trajectories" — skills that are used in similar contexts, regardless
of their semantic names.

This pezzo adds `cluster_by_sr_similarity(ids, M, threshold)` that
groups skills whose successor-rows are cosine-similar above the
threshold.

Three measurable invariants:

  1. SAME-FUTURE SKILLS CLUSTER: two skills that always lead to the
     same successor cluster end up in the same SR-cluster.

  2. DIFFERENT-FUTURE SKILLS DIVERGE: skills with disjoint successors
     cluster apart.

  3. EMPTY MATRIX: graceful handling.
"""
from __future__ import annotations

import numpy as np


def test_same_future_skills_cluster_together():
    """A and B are different skills (different ids) but BOTH lead to
    the same successor C with same probability. SR rows are similar
    → cluster together."""
    from engram.successor_repr import (
        build_successor_matrix,
        cluster_by_sr_similarity,
    )

    # Episodes: 5 with A→C, 5 with B→C. A and B both go to C.
    episodes = (
        [["A", "C"]] * 5
        + [["B", "C"]] * 5
        # Add D→E to make a separate cluster
        + [["D", "E"]] * 5
    )
    ids, M = build_successor_matrix(episodes, gamma=0.9)
    clusters = cluster_by_sr_similarity(ids, M, threshold=0.8)

    # Find which cluster each skill ended up in
    cluster_of = {}
    for ci, members in enumerate(clusters):
        for s in members:
            cluster_of[s] = ci

    assert cluster_of["A"] == cluster_of["B"], (
        f"A and B should cluster (both go to C); clusters={clusters}"
    )
    assert cluster_of["D"] != cluster_of["A"], (
        f"D shouldn't share cluster with A/B; clusters={clusters}"
    )


def test_different_future_skills_diverge():
    """Skills with disjoint successors should NOT cluster."""
    from engram.successor_repr import (
        build_successor_matrix,
        cluster_by_sr_similarity,
    )

    episodes = (
        [["A", "B"]] * 5
        + [["C", "D"]] * 5
    )
    ids, M = build_successor_matrix(episodes, gamma=0.9)
    clusters = cluster_by_sr_similarity(ids, M, threshold=0.7)

    cluster_of = {}
    for ci, members in enumerate(clusters):
        for s in members:
            cluster_of[s] = ci

    # A and C should be in different clusters (disjoint futures).
    assert cluster_of["A"] != cluster_of["C"], (
        f"A and C have disjoint futures, should cluster apart; {clusters}"
    )


def test_empty_matrix_returns_empty_clusters():
    """Empty SR matrix returns []."""
    from engram.successor_repr import cluster_by_sr_similarity

    out = cluster_by_sr_similarity([], np.zeros((0, 0), dtype=np.float32))
    assert out == []


def test_singleton_skill_is_own_cluster():
    """A single skill produces a single 1-element cluster."""
    from engram.successor_repr import (
        build_successor_matrix,
        cluster_by_sr_similarity,
    )

    ids, M = build_successor_matrix([["A"]], gamma=0.9)
    clusters = cluster_by_sr_similarity(ids, M, threshold=0.5)
    assert len(clusters) == 1
    assert clusters[0] == ["A"]
