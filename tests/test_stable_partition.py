"""Cycle 261 (2026-05-23) — RED contract for partition stabilization.

Real SOS mitigation (paper §6.5 promotion). Store partition assignment
at t0, force unchanged nodes to inherit at t1. Only new (injected)
nodes get fresh local-move Louvain assignment.

Acceptance criterion (falsifiable):
    Jaccard(P_t0, P_t1_stable) = 0.0 over the unchanged-node subset.
    Effect = Δ_treatment_stable - Δ_baseline ≤ 0.05 (within threshold).
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import numpy as np
import pytest


def _seed_simple_corpus(db_path: Path) -> None:
    """20 facts in 3 sub-themes connected via lineage chains."""
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("""
            CREATE TABLE facts (
                id TEXT PRIMARY KEY,
                topic TEXT,
                proposition TEXT,
                embedding BLOB,
                lineage_to TEXT,
                superseded_by TEXT,
                status TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE causal_edges (src TEXT, dst TEXT, weight REAL)
        """)
        rng = np.random.default_rng(7)
        for sub in range(3):
            for i in range(7):
                fid = f"s{sub}_f{i}"
                base = np.zeros(384, dtype=np.float32)
                base[(sub * 13) % 384] = 1.0
                emb = base + 0.05 * rng.standard_normal(384).astype(np.float32)
                parent = f"s{sub}_f{i-1}" if i > 0 else None
                conn.execute(
                    "INSERT INTO facts (id, topic, proposition, embedding, "
                    "lineage_to, status) VALUES (?, ?, ?, ?, ?, ?)",
                    (fid, f"p/sub{sub}", f"f{i}", emb.tobytes(), parent, None),
                )
                # dense intra-sub
                for j in range(i):
                    conn.execute(
                        "INSERT INTO causal_edges (src, dst, weight) "
                        "VALUES (?, ?, ?)",
                        (fid, f"s{sub}_f{j}", 1.0),
                    )
        conn.commit()
    finally:
        conn.close()


def test_inherits_unchanged_assignments(tmp_path: Path) -> None:
    """When no nodes added/removed, stable partition == original (Δ = 0)."""
    from engram.stable_partition import stable_partition

    db = tmp_path / "semantic.db"
    _seed_simple_corpus(db)
    p1 = stable_partition(db, seed=42)
    p2 = stable_partition(db, seed=42, prior_assignment=p1)
    # Same DB, prior assignment given → identical partition
    s1 = {frozenset(c) for c in p1.values_as_sets()}
    s2 = {frozenset(c) for c in p2.values_as_sets()}
    assert s1 == s2, f"Differs: {len(s1 ^ s2)} sets"


def test_new_nodes_get_assignment(tmp_path: Path) -> None:
    """When new facts are added, stable partition extends with assignments
    for the new nodes (not requiring re-partitioning the unchanged ones)."""
    from engram.stable_partition import stable_partition

    db = tmp_path / "semantic.db"
    _seed_simple_corpus(db)
    p1 = stable_partition(db, seed=42)
    n_old = len(p1.node_to_community)

    # Inject 5 new facts
    conn = sqlite3.connect(str(db))
    try:
        rng = np.random.default_rng(99)
        for i in range(5):
            base = np.zeros(384, dtype=np.float32)
            base[(0 * 13) % 384] = 1.0  # bias toward sub 0
            emb = base + 0.05 * rng.standard_normal(384).astype(np.float32)
            conn.execute(
                "INSERT INTO facts (id, topic, proposition, embedding, "
                "lineage_to, status) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    f"new_{i}",
                    "p/new",
                    f"new{i}",
                    emb.tobytes(),
                    "s0_f6",
                    None,
                ),
            )
        conn.commit()
    finally:
        conn.close()

    p2 = stable_partition(db, seed=42, prior_assignment=p1)
    # Old nodes preserve assignment
    for nid, cid in p1.node_to_community.items():
        assert p2.node_to_community.get(nid) == cid, (
            f"Node {nid} reassigned: {cid} -> {p2.node_to_community.get(nid)}"
        )
    # New nodes get assignment
    for i in range(5):
        assert f"new_{i}" in p2.node_to_community, (
            f"new_{i} got no assignment"
        )
    # Total nodes = old + new
    assert len(p2.node_to_community) == n_old + 5


def test_empty_db_returns_empty(tmp_path: Path) -> None:
    """Empty DB → empty partition."""
    from engram.stable_partition import stable_partition

    db = tmp_path / "semantic.db"
    conn = sqlite3.connect(str(db))
    try:
        conn.execute("""
            CREATE TABLE facts (
                id TEXT PRIMARY KEY, topic TEXT, proposition TEXT,
                embedding BLOB, lineage_to TEXT, superseded_by TEXT,
                status TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE causal_edges (src TEXT, dst TEXT, weight REAL)
        """)
        conn.commit()
    finally:
        conn.close()
    p = stable_partition(db, seed=42)
    assert p.node_to_community == {}


def test_missing_db_returns_empty(tmp_path: Path) -> None:
    """Missing DB → empty partition, no raise."""
    from engram.stable_partition import stable_partition

    p = stable_partition(tmp_path / "missing.db", seed=42)
    assert p.node_to_community == {}


def test_jaccard_zero_for_unchanged(tmp_path: Path) -> None:
    """ACCEPTANCE CRITERION (falsifiable): when prior_assignment is
    given for unchanged nodes, the resulting partition over those
    nodes is IDENTICAL → partition Jaccard distance = 0.0."""
    from engram.stable_partition import partition_jaccard, stable_partition

    db = tmp_path / "semantic.db"
    _seed_simple_corpus(db)
    p1 = stable_partition(db, seed=42)
    # Inject 3 new nodes (similar to test_new_nodes_get_assignment)
    conn = sqlite3.connect(str(db))
    try:
        rng = np.random.default_rng(11)
        for i in range(3):
            base = np.zeros(384, dtype=np.float32)
            base[0] = 1.0
            emb = base + 0.05 * rng.standard_normal(384).astype(np.float32)
            conn.execute(
                "INSERT INTO facts (id, topic, proposition, embedding, "
                "lineage_to, status) VALUES (?, ?, ?, ?, ?, ?)",
                (f"x_{i}", "p/x", f"x{i}", emb.tobytes(), "s0_f6", None),
            )
        conn.commit()
    finally:
        conn.close()
    p2 = stable_partition(db, seed=42, prior_assignment=p1)
    # Restrict to unchanged nodes (in p1)
    old_nodes = set(p1.node_to_community)
    # The partition Jaccard over unchanged nodes only:
    # For each node, both p1 and p2 should agree on community
    # → Jaccard = 0.0 over node-pair co-clustering.
    j = partition_jaccard(p1, p2, restrict_to=old_nodes)
    assert j == 0.0, f"Jaccard distance over unchanged nodes: {j}, expected 0"
