"""Cycle 253 (2026-05-23) — Architectural cure for singolarità #21.

The default single-pass Louvain over the agent's semantic-memory graph
develops "super-clusters": dominant communities that absorb new writes
without re-fragmenting. This is the structural side of observer-shift
(see ``docs/proposal/PAPER-21-OUTLINE.md``).

This module implements the **second-pass cure**: identify the master
super-cluster, build its induced subgraph, and re-run Louvain on it
recursively (depth-2). Returns the merged community list where the
master is replaced by its sub-communities (tagged ``from_master=True``).

Falsifiable acceptance criterion:
    Mean intra-cluster cohesion POST-cure must be ≥ pre-cure cohesion
    on the master super-cluster.

A4 onesti caveat:
    Adaptive thresholds (cycle 248-249) are tuning scaffolding. This
    module is the ARCHITECTURAL cure documented in cycle 252 dossier
    as "pending deferred". Replaces the tuning band-aid only when
    empirically validated (cohesion criterion).
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import networkx as nx
import numpy as np

from engram.community_detector import _load_graph, detect_communities


def _embeddings_for_ids(
    db_path: Path, ids: list[str],
) -> np.ndarray | None:
    """Fetch embeddings as (k, 384) float32 array. Returns ``None`` on
    failure or any missing row.

    Defensive: filters out rows with embedding ``length(embedding) != 1536``
    (i.e. NOT 384-dim float32), avoiding the np.stack shape-mismatch
    crash that bit us in cycle 172.
    """
    if not ids:
        return None
    try:
        conn = sqlite3.connect(str(db_path))
        try:
            placeholders = ",".join(["?"] * len(ids))
            rows = conn.execute(
                f"SELECT id, embedding FROM facts "  # noqa: S608
                f"WHERE id IN ({placeholders}) "
                f"AND length(embedding) = 1536",
                tuple(ids),
            ).fetchall()
        finally:
            conn.close()
    except sqlite3.Error:
        return None
    if not rows:
        return None
    by_id = {str(fid): blob for fid, blob in rows}
    parts: list[bytes] = []
    for fid in ids:
        if fid not in by_id:
            continue
        parts.append(by_id[fid])
    if not parts:
        return None
    arr = np.frombuffer(b"".join(parts), dtype=np.float32).reshape(-1, 384)
    return arr


def _cohesion_for_fact_ids(
    db_path: Path | str, ids: list[str],
) -> float:
    """Mean cosine of each row to the centroid for the given fact ids.

    Returns ``0.0`` on missing DB / no embeddings / degenerate centroid.
    Exposed as part of the public API for the falsifiability test
    (cohesion non-degrading criterion).
    """
    p = Path(db_path)
    if not p.exists() or not ids:
        return 0.0
    embs = _embeddings_for_ids(p, [str(i) for i in ids])
    if embs is None or embs.shape[0] == 0:
        return 0.0
    centroid = embs.mean(axis=0)
    cn = float(np.linalg.norm(centroid))
    if cn < 1e-9:
        return 0.0
    centroid_unit = centroid / cn
    norms = np.linalg.norm(embs, axis=1) + 1e-9
    cos = (embs @ centroid_unit) / norms
    return float(cos.mean())


def _reweight_subgraph_by_embedding(
    subgraph: nx.Graph,
    db_path: Path,
) -> nx.Graph:
    """Re-weight subgraph edges by embedding cosine similarity.

    Existing topological edges (lineage / causal) are KEPT — we don't
    introduce new edges, only adjust weights to reflect semantic
    similarity. Edges with cosine < 0 are floored to a small positive
    value so Louvain doesn't drop them entirely.

    This is the "multi-signal fusion" component of the cure: edge
    topology is *combined* with embedding geometry, not replaced. If
    two facts are graph-connected but embedding-distant, their edge
    weight drops → modularity favours separating them in the next
    Louvain pass.
    """
    nodes = list(subgraph.nodes())
    if not nodes:
        return subgraph
    embs = _embeddings_for_ids(db_path, [str(n) for n in nodes])
    if embs is None or embs.shape[0] != len(nodes):
        return subgraph  # cannot reweight — keep edge weights as-is

    # Normalised embeddings for fast cosine.
    norms = np.linalg.norm(embs, axis=1, keepdims=True) + 1e-9
    embs_n = embs / norms
    idx = {n: i for i, n in enumerate(nodes)}

    g_out = subgraph.copy()
    for u, v in list(g_out.edges()):
        cos = float(embs_n[idx[u]] @ embs_n[idx[v]])
        # Floor to small positive value (Louvain expects positive weights).
        w = max(cos, 0.01)
        g_out[u][v]["weight"] = w
    return g_out


def _louvain_on_subgraph(
    subgraph: nx.Graph,
    seed: int,
    min_size: int,
) -> list[list[str]]:
    """Run Louvain on a subgraph. Returns list of communities (node-id
    lists). Filters by ``min_size``.

    Defensive: empty subgraph → empty list; networkx error → empty list.
    """
    if subgraph.number_of_nodes() == 0:
        return []
    try:
        comms = nx.algorithms.community.louvain_communities(
            subgraph, weight="weight", seed=int(seed),
        )
    except Exception:  # noqa: BLE001 - defensive
        return []
    out: list[list[str]] = []
    for c in comms:
        nodes = sorted(str(n) for n in c)
        if len(nodes) < int(min_size):
            continue
        out.append(nodes)
    return out


def second_pass_louvain(
    semantic_db: Path | str,
    *,
    seed: int = 42,
    master_threshold_ratio: float = 0.5,
    min_community_size: int = 2,
    edges_source: str = "both",
) -> list[dict[str, Any]]:
    """Run first-pass Louvain, then re-run on the master super-cluster.

    Args:
        semantic_db: path to ``semantic.db``.
        seed: random seed for both passes (deterministic).
        master_threshold_ratio: a community is the "master super-cluster"
            iff ``len(c) >= master_threshold_ratio * total_alive_facts``.
            With 0.5, only a single dominant community qualifies. Lower
            values are more aggressive; pre-registered default 0.5.
        min_community_size: minimum size for returned communities.
        edges_source: "lineage" | "causal" | "both" — pass-through to
            ``community_detector._load_graph``.

    Returns:
        List of dicts:
        ``{community_id: str, fact_ids: list[str], from_master: bool,
           size: int}``
        Sorted by ``size`` desc.

    Defensive:
        * Missing DB / empty graph → ``[]``.
        * No master super-cluster (no community exceeds threshold) →
          returns first-pass communities verbatim, all with
          ``from_master=False``.
        * Master too small to fragment further (Louvain returns one
          community) → master kept as-is with ``from_master=False``.
    """
    p = Path(semantic_db)
    if not p.exists():
        return []

    # First-pass Louvain (reuse existing module).
    first = detect_communities(
        semantic_db=p,
        algorithm="louvain",
        edges_source=edges_source,  # type: ignore[arg-type]
        min_community_size=int(min_community_size),
        seed=int(seed),
    )
    first_communities = first.get("communities", [])
    if not first_communities:
        return []

    # Identify total alive facts (denominator for master threshold).
    try:
        conn = sqlite3.connect(str(p))
        try:
            row = conn.execute(
                "SELECT COUNT(*) FROM facts "
                "WHERE superseded_by IS NULL "
                "AND (status IS NULL OR status NOT IN "
                "('orphaned', 'quarantined'))",
            ).fetchone()
            total_alive = int(row[0]) if row else 0
        finally:
            conn.close()
    except sqlite3.Error:
        total_alive = sum(
            len(c.get("fact_ids", [])) for c in first_communities
        )

    threshold = float(master_threshold_ratio) * max(total_alive, 1)

    # Identify the master super-cluster (largest community above
    # threshold). If multiple communities exceed threshold, only the
    # single largest is treated as master (the partition is dominated).
    master_idx = -1
    master_size = -1
    for i, c in enumerate(first_communities):
        sz = len(c.get("fact_ids", []))
        if sz >= threshold and sz > master_size:
            master_idx = i
            master_size = sz

    # No master → pass-through first-pass results.
    if master_idx < 0:
        out_no_master: list[dict[str, Any]] = []
        for c in first_communities:
            fids = [str(x) for x in c.get("fact_ids", [])]
            if len(fids) < min_community_size:
                continue
            out_no_master.append({
                "community_id": str(c.get("id", "")),
                "fact_ids": fids,
                "from_master": False,
                "size": len(fids),
            })
        out_no_master.sort(key=lambda d: -d["size"])
        return out_no_master

    # Master exists → load full graph, induce subgraph, re-run Louvain.
    try:
        full_graph = _load_graph(p, edges_source)  # type: ignore[arg-type]
    except Exception:  # noqa: BLE001 - defensive
        # Loading failed → pass-through to avoid lying about cure
        return [
            {
                "community_id": str(c.get("id", "")),
                "fact_ids": [str(x) for x in c.get("fact_ids", [])],
                "from_master": False,
                "size": len(c.get("fact_ids", [])),
            }
            for c in first_communities
            if len(c.get("fact_ids", [])) >= min_community_size
        ]

    master_fact_ids = [
        str(x) for x in first_communities[master_idx].get("fact_ids", [])
    ]
    # Induce subgraph; defensive: drop nodes that may not be in full graph
    # (e.g. orphaned facts that slipped through filter inconsistencies).
    node_subset = [n for n in master_fact_ids if full_graph.has_node(n)]
    if not node_subset:
        # Cannot induce → pass-through with no fragmentation
        return [
            {
                "community_id": str(c.get("id", "")),
                "fact_ids": [str(x) for x in c.get("fact_ids", [])],
                "from_master": False,
                "size": len(c.get("fact_ids", [])),
            }
            for c in first_communities
            if len(c.get("fact_ids", [])) >= min_community_size
        ]
    subgraph = full_graph.subgraph(node_subset).copy()
    # MULTI-SIGNAL CURE: re-weight subgraph edges by embedding cosine so
    # Louvain can detect semantic sub-structure inside the topologically
    # uniform super-cluster. Without re-weighting, a clique-like master
    # cannot fragment (modularity is identical for any partition).
    subgraph = _reweight_subgraph_by_embedding(subgraph, p)
    sub_communities = _louvain_on_subgraph(
        subgraph, seed=seed, min_size=min_community_size,
    )

    # If second-pass returned only 1 community (or fewer than original
    # master), the master did NOT fragment. Keep master as a single
    # community with from_master=False (no cure applied).
    out: list[dict[str, Any]] = []
    if len(sub_communities) <= 1:
        out.append({
            "community_id": str(first_communities[master_idx].get("id", "")),
            "fact_ids": master_fact_ids,
            "from_master": False,
            "size": len(master_fact_ids),
        })
    else:
        # Master fragmented → tag each sub-community as from_master=True.
        for j, sub_ids in enumerate(sub_communities):
            out.append({
                "community_id": (
                    f"{first_communities[master_idx].get('id', 'master')}__sp{j}"
                ),
                "fact_ids": sub_ids,
                "from_master": True,
                "size": len(sub_ids),
            })

    # Append the OTHER first-pass communities unchanged.
    for i, c in enumerate(first_communities):
        if i == master_idx:
            continue
        fids = [str(x) for x in c.get("fact_ids", [])]
        if len(fids) < min_community_size:
            continue
        out.append({
            "community_id": str(c.get("id", "")),
            "fact_ids": fids,
            "from_master": False,
            "size": len(fids),
        })

    out.sort(key=lambda d: -d["size"])
    return out


__all__ = [
    "_cohesion_for_fact_ids",
    "second_pass_louvain",
]
