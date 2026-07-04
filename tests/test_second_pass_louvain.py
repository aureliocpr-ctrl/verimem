"""Cycle 253 (2026-05-23) — RED contract for second-pass Louvain cure.

Architectural cure for singolarità #21 (observer-shifts-emergence). The
default single-pass Louvain run on a self-modifying graph develops
"super-clusters" — dominant communities that absorb new writes without
re-fragmenting. The cure: re-run Louvain on the subgraph induced by the
master super-cluster (depth-2). Acceptance: intra-cluster cohesion
post-cure must be ≥ pre-cure across N=5 seeds.

This test file defines the CONTRACT before the implementation.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import numpy as np
import pytest


def _seed_corpus_with_super_cluster(db_path: Path, n_master: int = 30,
                                     n_outliers: int = 5) -> None:
    """Build a synthetic semantic.db with one giant lineage chain
    (master super-cluster) plus a few outlier islands.

    Edges via lineage_to → networkx will form one tightly connected
    component (the master) plus singletons (outliers).

    Scan #316 realignment: the causal clique used to live in a
    `causal_edges(src,dst)` table ON semantic.db — the exact broken
    schema/location the detector bug-fix removed (it was only ever read
    BECAUSE of the bug). The clique now uses the REAL wiring: episode ids
    in `facts.source_episodes` (comma-separated TEXT, like semantic.py
    stores it) + `causal_edges(src_episode_id, dst_episode_id, ...)` in
    the SIBLING episodes.db that `_sibling_episodes_db` derives — so
    ``db_path`` must live under a ``semantic/`` directory.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS facts (
                id TEXT PRIMARY KEY,
                topic TEXT,
                proposition TEXT,
                embedding BLOB,
                lineage_to TEXT,
                superseded_by TEXT,
                status TEXT,
                source_episodes TEXT
            )
        """)
        rng = np.random.default_rng(42)
        # Master: chain of n_master facts with similar embeddings (3 sub-themes)
        for i in range(n_master):
            sub = i % 3  # 3 sub-themes within the master
            base = np.array([1.0 if j == sub else 0.0 for j in range(384)],
                            dtype=np.float32)
            emb = base + 0.1 * rng.standard_normal(384).astype(np.float32)
            emb_blob = emb.tobytes()
            parent = f"master_{i-1}" if i > 0 else None
            conn.execute(
                "INSERT INTO facts (id, topic, proposition, embedding, "
                "lineage_to, status, source_episodes) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    f"master_{i}",
                    f"project/master/subtheme_{sub}",
                    f"master fact {i} subtheme {sub}",
                    emb_blob,
                    parent,
                    None,
                    f"ep_{i}",
                ),
            )
        conn.commit()
    finally:
        conn.close()
    # Causal edges: full clique intra-master → super-cluster pathology
    # (first-pass Louvain sees ONE big community because topology is
    # uniform). Sub-structure exists ONLY at embedding level (3 distinct
    # sub-themes). REAL schema/location: sibling episodes.db.
    ep_db = db_path.parent.parent / "episodes" / "episodes.db"
    ep_db.parent.mkdir(parents=True, exist_ok=True)
    ep_conn = sqlite3.connect(str(ep_db))
    try:
        ep_conn.execute("""
            CREATE TABLE IF NOT EXISTS causal_edges (
                src_episode_id TEXT NOT NULL,
                dst_episode_id TEXT NOT NULL,
                via_skill_id TEXT NOT NULL,
                weight REAL NOT NULL,
                PRIMARY KEY (src_episode_id, dst_episode_id, via_skill_id)
            )
        """)
        n_master_local = n_master
        for i in range(n_master_local):
            for j in range(i + 1, n_master_local):
                ep_conn.execute(
                    "INSERT OR IGNORE INTO causal_edges VALUES (?, ?, ?, ?)",
                    (f"ep_{i}", f"ep_{j}", "s1", 1.0),
                )
        ep_conn.commit()
    finally:
        ep_conn.close()
    conn = sqlite3.connect(str(db_path))
    try:
        # Outliers: singleton islands
        for j in range(n_outliers):
            base = np.zeros(384, dtype=np.float32)
            base[100 + j] = 1.0
            emb = base + 0.05 * rng.standard_normal(384).astype(np.float32)
            conn.execute(
                "INSERT INTO facts (id, topic, proposition, embedding, "
                "lineage_to, status) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    f"outlier_{j}",
                    f"project/outlier_{j}",
                    f"outlier {j}",
                    emb.tobytes(),
                    None,
                    None,
                ),
            )
        conn.commit()
    finally:
        conn.close()


def test_returns_list(tmp_path: Path) -> None:
    """Second-pass Louvain returns a list of community dicts."""
    from engram.second_pass_louvain import second_pass_louvain

    db = tmp_path / "semantic" / "semantic.db"
    _seed_corpus_with_super_cluster(db)
    result = second_pass_louvain(db, seed=42)
    assert isinstance(result, list)


def test_empty_db_returns_empty(tmp_path: Path) -> None:
    """No facts → empty result, no raise."""
    from engram.second_pass_louvain import second_pass_louvain

    db = tmp_path / "semantic.db"
    conn = sqlite3.connect(str(db))
    try:
        conn.execute("""
            CREATE TABLE facts (
                id TEXT PRIMARY KEY, topic TEXT, proposition TEXT,
                embedding BLOB, lineage_to TEXT, superseded_by TEXT, status TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE causal_edges (src TEXT, dst TEXT)
        """)
        conn.commit()
    finally:
        conn.close()
    assert second_pass_louvain(db, seed=42) == []


def test_missing_db_returns_empty(tmp_path: Path) -> None:
    """Missing DB → empty, no raise."""
    from engram.second_pass_louvain import second_pass_louvain

    result = second_pass_louvain(tmp_path / "does_not_exist.db", seed=42)
    assert result == []


def test_fragments_master_super_cluster(tmp_path: Path) -> None:
    """Master super-cluster with 3 sub-themes must be fragmented into
    ≥2 sub-communities by second-pass."""
    from engram.community_detector import detect_communities
    from engram.second_pass_louvain import second_pass_louvain

    db = tmp_path / "semantic" / "semantic.db"
    _seed_corpus_with_super_cluster(db, n_master=30, n_outliers=3)

    # First-pass baseline: master is one big community
    first = detect_communities(
        semantic_db=db,
        algorithm="louvain",
        edges_source="both",
        min_community_size=2,
        seed=42,
    )
    first_communities = first.get("communities", [])
    master_size = max(
        (len(c.get("fact_ids", [])) for c in first_communities), default=0
    )
    assert master_size >= 20, (
        f"Test setup invalid: master not dominant, max size {master_size}"
    )

    # Second-pass: master fragmented
    second = second_pass_louvain(
        db, seed=42, master_threshold_ratio=0.5,
    )
    # Returned list of communities post-cure: master should be replaced
    # by ≥2 sub-communities, each smaller than the original master.
    master_origin_subs = [
        c for c in second if c.get("from_master") is True
    ]
    assert len(master_origin_subs) >= 2, (
        f"Master not fragmented: got {len(master_origin_subs)} sub-communities"
    )
    for c in master_origin_subs:
        assert len(c.get("fact_ids", [])) < master_size, (
            f"Sub-community size {len(c.get('fact_ids', []))} not < "
            f"master size {master_size}"
        )


def test_preserves_non_master_communities(tmp_path: Path) -> None:
    """Non-master communities are passed through unchanged."""
    from engram.second_pass_louvain import second_pass_louvain

    db = tmp_path / "semantic.db"
    # Build TWO comparable clusters of size 8 each + small island.
    conn = sqlite3.connect(str(db))
    try:
        conn.execute("""
            CREATE TABLE facts (
                id TEXT PRIMARY KEY, topic TEXT, proposition TEXT,
                embedding BLOB, lineage_to TEXT, superseded_by TEXT, status TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE causal_edges (src TEXT, dst TEXT)
        """)
        rng = np.random.default_rng(7)
        for cluster_id in range(2):
            for i in range(8):
                base = np.zeros(384, dtype=np.float32)
                base[cluster_id * 10] = 1.0
                emb = base + 0.05 * rng.standard_normal(384).astype(np.float32)
                parent = f"c{cluster_id}_{i-1}" if i > 0 else None
                conn.execute(
                    "INSERT INTO facts (id, topic, proposition, embedding, "
                    "lineage_to, status) VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        f"c{cluster_id}_{i}",
                        f"project/cluster{cluster_id}",
                        f"c{cluster_id}_{i}",
                        emb.tobytes(),
                        parent,
                        None,
                    ),
                )
        conn.commit()
    finally:
        conn.close()

    result = second_pass_louvain(
        db, seed=42, master_threshold_ratio=0.7,
    )
    # With two comparable clusters, NEITHER triggers "master" threshold.
    # All returned communities should be from_master=False.
    assert all(c.get("from_master") is False for c in result), (
        "No cluster should be tagged as fragmented master in this setup"
    )
    # And we should still see the 2 clusters present.
    assert len(result) >= 2


def test_seed_deterministic(tmp_path: Path) -> None:
    """Same seed → identical communities ordering."""
    from engram.second_pass_louvain import second_pass_louvain

    db = tmp_path / "semantic.db"
    _seed_corpus_with_super_cluster(db, n_master=20, n_outliers=3)

    r1 = second_pass_louvain(db, seed=42, master_threshold_ratio=0.5)
    r2 = second_pass_louvain(db, seed=42, master_threshold_ratio=0.5)
    # Order may differ but set of frozenset(fact_ids) must match.
    s1 = {frozenset(c["fact_ids"]) for c in r1}
    s2 = {frozenset(c["fact_ids"]) for c in r2}
    assert s1 == s2, (
        f"Non-deterministic: {len(s1 ^ s2)} differing communities"
    )


def test_cohesion_non_degrading(tmp_path: Path) -> None:
    """Cohesion criterion (falsifiable): mean intra-cluster cohesion
    POST-cure must be ≥ PRE-cure cohesion on the master.

    This is the falsifiable claim of cycle 253: if cohesion DROPS, the
    cure is rejected.
    """
    from engram.community_detector import detect_communities
    from engram.second_pass_louvain import (
        _cohesion_for_fact_ids,
        second_pass_louvain,
    )

    db = tmp_path / "semantic.db"
    _seed_corpus_with_super_cluster(db, n_master=30, n_outliers=3)

    # Pre-cure: cohesion of the master super-cluster
    first = detect_communities(
        semantic_db=db,
        algorithm="louvain",
        edges_source="both",
        min_community_size=2,
        seed=42,
    )
    master_ids = max(
        (c.get("fact_ids", []) for c in first.get("communities", [])),
        key=len,
        default=[],
    )
    pre_cohesion = _cohesion_for_fact_ids(db, [str(i) for i in master_ids])

    # Post-cure: mean cohesion of sub-communities
    second = second_pass_louvain(db, seed=42, master_threshold_ratio=0.5)
    master_subs = [c for c in second if c.get("from_master") is True]
    if not master_subs:
        pytest.skip("Master not fragmented; cohesion test N/A")
    sub_cohesions = [
        _cohesion_for_fact_ids(db, c["fact_ids"]) for c in master_subs
    ]
    post_mean = float(np.mean(sub_cohesions))

    # Falsifiable assertion: post mean must be ≥ pre cohesion.
    # Tolerance: 0.02 (small) to account for variance in synthetic data.
    assert post_mean + 0.02 >= pre_cohesion, (
        f"Cure DEGRADED cohesion: pre={pre_cohesion:.3f}, "
        f"post mean={post_mean:.3f}. Cycle 253 hypothesis FALSIFIED on "
        f"this synthetic corpus."
    )
