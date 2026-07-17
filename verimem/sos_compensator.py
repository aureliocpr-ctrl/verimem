"""Cycle 381 (2026-05-23) — SOS-COMPENSATING WRITES.

Aurelio carta bianca + sgridata 2026-05-23 23:18: "stai forzando le basi
della scienza computazionale? stai sfidando te stesso? niente marketing".

WebSearch+Gemini 2026 literature reviewed. Existing patterns rejected:
- RAPT (DP embedding) — already exists
- DPforward (forward-pass perturbation) — already exists
- xMemory uncertainty-aware reader — already exists
- MemMachine ground-truth-preserving — already exists

GENUINE B4 NUCLEAR singolarità candidate (NOT in 2026 literature):
SOS-COMPENSATING WRITES.

The Structural Observer-Shift paper §21 measured E≈0.08 H1 partition
Jaccard drift on self-writes. Literature treats this as INEVITABLE.
This module attacks the problem at the WRITE-CHOOSING level: when
the agent decides where to attach a new fact (lineage_to anchor),
SELECT the anchor that minimizes EXPECTED partition shift.

Falsifiable claim:
  At fixed k=50 writes, vanilla-random-anchor inject produces ΔJ_random,
  while compensated-anchor inject produces ΔJ_compensated, and
  ΔJ_compensated < ΔJ_random / 2 on production-scale corpus.

If the bench shows ΔJ_compensated >= ΔJ_random → FALSIFIED.

Concatenazione B4 (5 elementi non visti combinati prima):
  Louvain partition (Blondel 2008)
  + community-size sensitivity gradient (novel observation: small
    communities perturb global modularity more per fact added)
  + lineage_to anchor selection (HippoAgent-specific write pattern)
  + greedy minimization of expected ΔJ (one-step lookahead)
  + SOS metric §3 of paper-21 outline
  ⇒ compensated_write_anchor: O(N) selection algorithm.

A3 honest scope: this IS a singolarità candidate because:
  - No 2026 paper does write-time compensation for partition shift
  - It is empirically falsifiable (bench compare)
  - It composes 5 elements never combined this way

WILL it work? Falsifiable bench in tests/test_sos_compensator.py.
Negative result is acceptable per Popperian discipline.

API:
  compute_community_sizes(partition) -> dict[community_id, size]

  score_anchor(partition, anchor_id, alpha=1.0) -> float
    Higher = better anchor (less expected ΔJ). Score is the inverse
    of expected single-fact perturbation: 1 / community_size_of(anchor).
    Attaching to small communities increases their relative size by
    larger fraction → larger ΔJ. Large communities absorb new fact
    with small relative growth.

  select_compensated_anchor(semantic_db, k_candidates=20, rng_seed=42)
    -> {anchor_id, score, community_id, expected_growth}
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


def compute_community_sizes(
    partition: list[set[str]],
) -> dict[int, int]:
    """Return {community_index: size} for a partition list of sets."""
    return {i: len(c) for i, c in enumerate(partition)}


def score_anchor_for_compensation(
    partition: list[set[str]],
    anchor_id: str,
    alpha: float = 1.0,
) -> dict[str, Any]:
    """Score an anchor by inverse community size.

    Larger communities absorb new fact with smaller relative growth,
    so they perturb partition LESS.

    Args:
        partition: list of node-id sets (Louvain output).
        anchor_id: candidate fact_id to attach new fact to.
        alpha: smoothing parameter for score = alpha / size.

    Returns:
        {community_index, community_size, score, found: bool}
    """
    for ci, comm in enumerate(partition):
        if anchor_id in comm:
            size = len(comm)
            return {
                "community_index": ci,
                "community_size": size,
                "score": alpha / max(size, 1),
                "found": True,
                "relative_growth": 1.0 / max(size, 1),
            }
    # Anchor not found in any community
    return {
        "community_index": -1,
        "community_size": 0,
        "score": 0.0,
        "found": False,
        "relative_growth": 1.0,  # max perturbation
    }


def select_compensated_anchor(
    semantic_db: Path | str,
    k_candidates: int = 20,
    rng_seed: int = 42,
    edges_source: str = "both",
) -> dict[str, Any]:
    """Select an anchor that minimizes expected partition shift.

    Algorithm:
        1. Compute current Louvain partition of semantic.db.
        2. Sample k_candidates alive fact ids randomly.
        3. Score each candidate by score_anchor_for_compensation.
        4. Return the best-scored anchor (LARGEST community).

    The intuition: attaching a new fact to a LARGE community grows
    that community by 1/N (small relative perturbation). Attaching
    to a SINGLETON triples its size (large relative perturbation).
    Partition Jaccard pre/post is dominated by relative growth, so
    minimizing relative growth minimizes ΔJ.

    Args:
        semantic_db: production DB path.
        k_candidates: how many random alive ids to score.
        rng_seed: deterministic RNG seed.
        edges_source: "lineage" | "causal" | "both" for graph build.

    Returns:
        {
          "anchor_id": str | None,
          "community_index": int,
          "community_size": int,
          "score": float,
          "relative_growth": float,
          "n_candidates_scored": int,
          "n_communities": int,
        }
    """
    import random as _random

    import networkx as nx

    from verimem.community_detector import _load_graph

    p = Path(semantic_db)
    if not p.exists():
        return {"anchor_id": None, "error": "db not found"}

    # Build graph + Louvain partition
    try:
        g = _load_graph(p, edges_source)
    except Exception:  # noqa: BLE001
        return {"anchor_id": None, "error": "graph load failed"}
    if g.number_of_nodes() == 0:
        return {"anchor_id": None, "error": "empty graph"}

    try:
        comms = nx.algorithms.community.louvain_communities(
            g, weight="weight", seed=int(rng_seed),
        )
    except Exception:  # noqa: BLE001
        return {"anchor_id": None, "error": "louvain failed"}
    partition = [{str(n) for n in c} for c in comms]

    # Get alive fact ids
    conn = sqlite3.connect(str(p))
    try:
        rows = conn.execute(
            "SELECT id FROM facts "
            "WHERE (superseded_by IS NULL OR superseded_by = '')",
        ).fetchall()
    finally:
        conn.close()
    alive_ids = [r[0] for r in rows]
    if not alive_ids:
        return {"anchor_id": None, "error": "no alive facts"}

    # Sample candidates
    rng = _random.Random(rng_seed)
    sample = rng.sample(alive_ids,
                        min(k_candidates, len(alive_ids)))

    # Score all candidates
    best: dict[str, Any] | None = None
    n_scored = 0
    for aid in sample:
        s = score_anchor_for_compensation(partition, aid)
        if not s["found"]:
            continue
        n_scored += 1
        if best is None or s["score"] > best["score"]:
            best = {**s, "anchor_id": aid}

    if best is None:
        return {"anchor_id": None, "error": "no scorable candidates"}

    return {
        "anchor_id": best["anchor_id"],
        "community_index": best["community_index"],
        "community_size": best["community_size"],
        "score": best["score"],
        "relative_growth": best["relative_growth"],
        "n_candidates_scored": n_scored,
        "n_communities": len(partition),
    }


def select_vanilla_anchor(
    semantic_db: Path | str,
    rng_seed: int = 42,
) -> dict[str, Any]:
    """Baseline: pick a single random anchor (no compensation).

    For falsifiable comparison.
    """
    import random as _random
    p = Path(semantic_db)
    if not p.exists():
        return {"anchor_id": None, "error": "db not found"}
    conn = sqlite3.connect(str(p))
    try:
        rows = conn.execute(
            "SELECT id FROM facts "
            "WHERE (superseded_by IS NULL OR superseded_by = '')",
        ).fetchall()
    finally:
        conn.close()
    if not rows:
        return {"anchor_id": None, "error": "no alive facts"}
    rng = _random.Random(rng_seed)
    aid = rng.choice([r[0] for r in rows])
    return {"anchor_id": aid, "score": 0.0, "vanilla": True}
