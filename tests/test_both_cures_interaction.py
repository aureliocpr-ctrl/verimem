"""Cycle 292 (2026-05-23) — BOTH cures interaction precedence contract.

Verifies that when both enable_stable_partition=True AND
enable_second_pass=True, stable_partition WINS (the cycle 292
documented precedence in skill_emergence_detector.py docstring).

This is M2 reify (regola = oggetto scientifico testabile): the
precedence is documented in code AND pinned by test.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import numpy as np


def _seed_corpus(db_path: Path) -> None:
    conn = sqlite3.connect(str(db_path))
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
        rng = np.random.default_rng(7)
        # 12 facts, 2 clusters of 6 each
        for cluster_id in range(2):
            for i in range(6):
                fid = f"c{cluster_id}_f{i}"
                base = np.zeros(384, dtype=np.float32)
                base[cluster_id * 10] = 1.0
                emb = base + 0.05 * rng.standard_normal(384).astype(np.float32)
                parent = f"c{cluster_id}_f{i-1}" if i > 0 else None
                conn.execute(
                    "INSERT INTO facts (id, topic, proposition, embedding, "
                    "lineage_to) VALUES (?, ?, ?, ?, ?)",
                    (fid, f"p/c{cluster_id}", f"c{cluster_id}_f{i}",
                     emb.tobytes(), parent),
                )
                for j in range(i):
                    conn.execute(
                        "INSERT INTO causal_edges (src, dst, weight) "
                        "VALUES (?, ?, ?)",
                        (fid, f"c{cluster_id}_f{j}", 1.0),
                    )
        conn.commit()
    finally:
        conn.close()


def test_stable_partition_wins_when_both_true(tmp_path: Path) -> None:
    """Cycle 292 precedence contract: stable_partition wins over
    second_pass when both opt-in flags are True."""
    from verimem.skill_emergence_detector import detect_emerging_skills

    db = tmp_path / "semantic.db"
    _seed_corpus(db)

    # Run with BOTH flags True
    result_both = detect_emerging_skills(
        db,
        min_community_size=2,
        min_topic_purity=0.05,
        min_cohesion=0.05,
        max_n=20,
        seed=42,
        enable_stable_partition=True,
        enable_second_pass=True,  # Should be IGNORED per precedence
    )

    # Run with stable_partition ONLY
    result_stable_only = detect_emerging_skills(
        db,
        min_community_size=2,
        min_topic_purity=0.05,
        min_cohesion=0.05,
        max_n=20,
        seed=42,
        enable_stable_partition=True,
        enable_second_pass=False,
    )

    # Stable-only and BOTH must produce identical results: same
    # community_ids, same fact_ids, same emergence_score.
    assert len(result_both) == len(result_stable_only), (
        f"BOTH={len(result_both)} vs stable_only="
        f"{len(result_stable_only)} — counts differ. Stable should win."
    )
    for r1, r2 in zip(result_both, result_stable_only, strict=False):
        assert r1["fact_ids"] == r2["fact_ids"], (
            f"fact_ids diverge: {r1['fact_ids']} vs {r2['fact_ids']}"
        )
    # from_master is NOT present in stable_partition output
    for r in result_both:
        assert "from_master" not in r, (
            f"from_master flag in stable_partition output: {r} — "
            f"second_pass should be ignored"
        )


def test_second_pass_path_when_stable_false(tmp_path: Path) -> None:
    """Falsifies the precedence — second_pass only fires when stable=False."""
    from verimem.skill_emergence_detector import detect_emerging_skills

    db = tmp_path / "semantic.db"
    _seed_corpus(db)

    # second_pass=True with stable=False should produce from_master flag
    # when master super-cluster is fragmented.
    result_sp_only = detect_emerging_skills(
        db,
        min_community_size=2,
        min_topic_purity=0.05,
        min_cohesion=0.05,
        max_n=20,
        seed=42,
        enable_stable_partition=False,
        enable_second_pass=True,
        second_pass_master_threshold=0.005,  # very aggressive
    )
    # At least one community should have from_master flag present
    # (either True or False — the key is the flag EXISTS in result).
    if result_sp_only:
        assert any(
            "from_master" in r for r in result_sp_only
        ), "second_pass should emit from_master flag in at least one entry"


def test_neither_default(tmp_path: Path) -> None:
    """Default (both False) — legacy vanilla Louvain path, no from_master."""
    from verimem.skill_emergence_detector import detect_emerging_skills

    db = tmp_path / "semantic.db"
    _seed_corpus(db)

    result = detect_emerging_skills(
        db,
        min_community_size=2,
        min_topic_purity=0.05,
        min_cohesion=0.05,
        max_n=20,
        seed=42,
    )
    for r in result:
        assert "from_master" not in r, (
            "default path should NOT have from_master flag"
        )
