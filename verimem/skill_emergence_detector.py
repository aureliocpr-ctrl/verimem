"""Cycle 213 (2026-05-23) — BREAK PATTERN: skill_emergence detector.

Inspired by SOTA 2026 (MemOS cross-task skill reuse, MemMachine
contextualized retrieval). Detects facts clusters that are ready to
crystallise into a NEW skill — the missing primitive between
``verimem.consolidation`` (pairwise greedy, cycle #144) and
``verimem.dream.propose_dream_tasks`` (cluster → LLM synthesis, cycle
#34/#35).

Algorithm
---------
Compose THREE signals already shipped this session:
  1. **Community membership** (cycle 186 Louvain) — topological cohesion.
  2. **Topic frequency** (cycle 196 rank list builders) — semantic theme.
  3. **Embedding centroid distance** (numpy direct) — geometric cohesion.

A fact-cluster scores as "emergent skill candidate" when:
  - It's a Louvain community of size ≥ min_size.
  - ≥ 60% of facts share the same dominant topic OR topic prefix.
  - The intra-community embedding cosine variance is < threshold.

Output: list of ``(skill_name_suggestion, member_fact_ids, evidence)``
ranked by emergence_score (cohesion × size × topic_purity).

Why singularity-class
---------------------
HippoAgent currently REQUIRES an LLM call (``propose_dream_tasks``)
to even DETECT skill candidates. This module detects them PURELY
algorithmically from existing graph + embedding state. The LLM call
is then a NAMING + BODY-WRITING step, NOT a discovery step. That's a
qualitative jump in autonomy: the system can flag "skill X is
emerging" without consuming any token budget.

Defensive
---------
* Missing DB / SQL error / empty graph → ``[]``, never raises.
* Communities below ``min_community_size`` → silently dropped.
* No topic majority → cluster still listed but with empty
  ``suggested_skill_name``.
"""
from __future__ import annotations

import sqlite3
from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np

from verimem.community_detector import detect_communities
from verimem.embedding import expected_embedding_bytes
from verimem.topic_normalization import normalize_topic

if TYPE_CHECKING:
    from verimem.stable_partition import Partition


def _embeddings_for_ids(
    db_path: Path, ids: list[str],
) -> np.ndarray | None:
    """Fetch embeddings as a (k, 384) float32 array. ``None`` on
    failure or any missing row."""
    if not ids:
        return None
    try:
        conn = sqlite3.connect(str(db_path))
        try:
            placeholders = ",".join(["?"] * len(ids))
            rows = conn.execute(
                f"SELECT id, embedding FROM facts "  # noqa: S608
                f"WHERE id IN ({placeholders}) "
                f"AND length(embedding) = ?",
                (*ids, expected_embedding_bytes()),
            ).fetchall()
        finally:
            conn.close()
    except sqlite3.Error:
        return None
    if not rows or len(rows) != len(ids):
        return None
    # Preserve order requested.
    by_id = {str(fid): blob for fid, blob in rows}
    parts: list[bytes] = []
    for fid in ids:
        if fid not in by_id:
            return None
        parts.append(by_id[fid])
    # dim-agnostic: derive the embedding width from the actual blob bytes, so a
    # 768-dim corpus (the production default) works. Audit R1 #1: the hardcoded
    # 384 / length=1536 left the whole detector silently dead on 768-dim.
    arr = np.frombuffer(b"".join(parts), dtype=np.float32).reshape(len(ids), -1)
    return arr


def _topic_for_ids(
    db_path: Path, ids: list[str],
) -> dict[str, str]:
    if not ids:
        return {}
    try:
        conn = sqlite3.connect(str(db_path))
        try:
            placeholders = ",".join(["?"] * len(ids))
            rows = conn.execute(
                f"SELECT id, topic FROM facts "  # noqa: S608
                f"WHERE id IN ({placeholders})",
                tuple(ids),
            ).fetchall()
        finally:
            conn.close()
    except sqlite3.Error:
        return {}
    return {str(fid): str(top or "") for fid, top in rows}


def _cohesion_score(embs: np.ndarray) -> float:
    """Mean cosine of each row to the centroid. Higher = more cohesive."""
    if embs.shape[0] == 0:
        return 0.0
    centroid = embs.mean(axis=0)
    cn = float(np.linalg.norm(centroid))
    if cn < 1e-9:
        return 0.0
    centroid_unit = centroid / cn
    norms = np.linalg.norm(embs, axis=1) + 1e-9
    cos = (embs @ centroid_unit) / norms
    return float(cos.mean())


def _suggest_skill_name(topic_counts: dict[str, int]) -> str:
    if not topic_counts:
        return ""
    top_topic, top_count = max(topic_counts.items(), key=lambda kv: kv[1])
    if not top_topic:
        return ""
    # Use the leaf of a slash-separated topic path as the candidate
    # skill name root.
    leaf = top_topic.rsplit("/", 1)[-1]
    return f"emerging_skill_{leaf}"


def detect_emerging_skills(
    semantic_db: Path | str,
    *,
    min_community_size: int = 4,
    min_topic_purity: float = 0.6,
    min_cohesion: float = 0.3,
    max_n: int = 10,
    seed: int = 42,
    enable_second_pass: bool = False,
    second_pass_master_threshold: float = 0.01,
    enable_stable_partition: bool = False,
    prior_partition: Partition | None = None,
    enable_hybrid: bool = False,
) -> list[dict[str, Any]]:
    """Detect emergent skill candidates in the fact graph.

    Args:
        semantic_db: path to ``semantic.db``.
        min_community_size: filter for Louvain communities (cycle 186).
        min_topic_purity: fraction of community members that must
            share the dominant topic.
        min_cohesion: minimum embedding-centroid cosine.
        max_n: cap on returned candidates.
        seed: pass-through to ``detect_communities``.
        enable_second_pass: when True, apply the cycle 253 architectural
            cure (``second_pass_louvain``): fragment the master
            super-cluster via embedding-weighted Louvain. Opt-in
            (default False) so existing callers / tests are unchanged.
            Mitigates singolarità #21 by re-fragmenting the dominant
            community that otherwise absorbs new writes without
            re-splitting.
        second_pass_master_threshold: ``master_threshold_ratio`` passed
            to ``second_pass_louvain``. Only used when
            ``enable_second_pass=True``.

    Returns:
        ``[{community_id, size, fact_ids, suggested_skill_name,
            dominant_topic, topic_purity, cohesion,
            emergence_score, from_master?}, ...]`` sorted by
        emergence_score DESC. ``from_master`` flag is present only
        when ``enable_second_pass=True``.

    Precedence (cycle 292):
        When both ``enable_stable_partition=True`` AND
        ``enable_second_pass=True``, ``enable_stable_partition`` WINS
        (the if/elif chain checks stable first). The two cures address
        different aspects of singolarità #21:

        - ``enable_stable_partition`` (cycle 261): operates at partition
          assignment level — prevents observer-shift across writes
          (paper §6.5). Real SOS mitigation.
        - ``enable_second_pass`` (cycle 253): operates at community
          fragmentation level — reveals latent candidates inside
          master super-cluster (paper §6.4). Detection enhancement.

        Activating BOTH is currently a no-op for second-pass: stable
        partition computes communities directly without recursive
        Louvain. Future work: a HYBRID mode that runs second-pass
        within each stable community (cycle 293+).
    """
    p = Path(semantic_db)
    if not p.exists():
        return []

    if enable_hybrid:
        # Cycle 295: HYBRID mode (composes stable_partition + second_pass).
        # Run stable_partition first for partition stability, then
        # second_pass_louvain WITHIN each stable community larger than
        # 1.5x min_community_size to reveal latent sub-structure.
        from verimem.community_detector import _load_graph
        from verimem.second_pass_louvain import (
            _louvain_on_subgraph,
            _reweight_subgraph_by_embedding,
        )
        from verimem.stable_partition import stable_partition
        sp_result = stable_partition(
            p,
            seed=int(seed),
            prior_assignment=prior_partition,
            edges_source="both",
        )
        from collections import defaultdict as _dd
        grouped: dict[str, list[str]] = _dd(list)
        for node, cid in sp_result.node_to_community.items():
            grouped[cid].append(str(node))

        full_graph = _load_graph(p, "both")  # type: ignore[arg-type]
        communities = []
        threshold = max(int(min_community_size * 1.5), 4)
        for cid, fids in grouped.items():
            if len(fids) >= threshold:
                # Try sub-fragmentation via second_pass
                node_subset = [n for n in fids if full_graph.has_node(n)]
                if node_subset:
                    subgraph = full_graph.subgraph(node_subset).copy()
                    subgraph = _reweight_subgraph_by_embedding(subgraph, p)
                    sub_comms = _louvain_on_subgraph(
                        subgraph, seed=int(seed),
                        min_size=int(min_community_size),
                    )
                    if len(sub_comms) > 1:
                        for j, sub_ids in enumerate(sub_comms):
                            communities.append({
                                "id": f"{cid}__hy{j}",
                                "fact_ids": sub_ids,
                                "from_hybrid": True,
                            })
                        continue
            # Fall-through: keep stable community as-is
            if len(fids) >= int(min_community_size):
                communities.append({
                    "id": cid,
                    "fact_ids": sorted(fids),
                    "from_hybrid": False,
                })
        communities.sort(key=lambda d: -len(d["fact_ids"]))
    elif enable_stable_partition:
        # Cycle 263: use the partition stabilisation cure. Pass-through
        # prior_assignment so unchanged-node assignments are preserved
        # across self-writes (real SOS mitigation).
        from verimem.stable_partition import stable_partition
        sp_result = stable_partition(
            p,
            seed=int(seed),
            prior_assignment=prior_partition,
            edges_source="both",
        )
        # Adapt to the dict shape used downstream.
        # Group by community_id → fact_ids list, filter by min size.
        from collections import defaultdict as _dd
        grouped: dict[str, list[str]] = _dd(list)
        for node, cid in sp_result.node_to_community.items():
            grouped[cid].append(str(node))
        communities = [
            {"id": cid, "fact_ids": sorted(fids)}
            for cid, fids in grouped.items()
            if len(fids) >= int(min_community_size)
        ]
        communities.sort(key=lambda d: -len(d["fact_ids"]))
    elif enable_second_pass:
        # Cycle 260: use the second-pass cure. Returns list of dicts with
        # `fact_ids`, `from_master`, `community_id`, `size`. Adapter to
        # the legacy `communities` shape (with `id` and `fact_ids`) below.
        from verimem.second_pass_louvain import second_pass_louvain
        sp_communities = second_pass_louvain(
            p,
            seed=int(seed),
            master_threshold_ratio=float(second_pass_master_threshold),
            min_community_size=int(min_community_size),
            edges_source="both",
        )
        # Adapt to the dict shape used downstream.
        communities = [
            {
                "id": c.get("community_id", ""),
                "fact_ids": c.get("fact_ids", []),
                "from_master": c.get("from_master", False),
            }
            for c in sp_communities
        ]
    else:
        result = detect_communities(
            semantic_db=p,
            algorithm="louvain",
            edges_source="both",
            min_community_size=int(min_community_size),
            seed=int(seed),
        )
        communities = result.get("communities", [])
    if not communities:
        return []

    out: list[dict[str, Any]] = []
    for c in communities:
        fact_ids = [str(fid) for fid in c.get("fact_ids", [])]
        if len(fact_ids) < int(min_community_size):
            continue
        topics_by_id = _topic_for_ids(p, fact_ids)
        # Cycle 215: normalise topics into 'family keys' so
        # 'project/hippoagent/cycle175' and 'cycle/175.1' both map
        # to the same key. Closes the topic-sparse finding of cycle 213.
        # Empty topics are filtered out (they contribute no signal).
        normalised = [normalize_topic(t) for t in topics_by_id.values()]
        non_empty_topics = [t for t in normalised if t]
        if not non_empty_topics:
            continue
        topic_counts = Counter(non_empty_topics)
        top_topic, top_count = max(
            topic_counts.items(), key=lambda kv: kv[1],
        )
        # Purity is over the WHOLE community size (empty-topic
        # facts count as "no signal" → they dilute purity).
        purity = top_count / len(fact_ids)
        if purity < float(min_topic_purity):
            continue
        embs = _embeddings_for_ids(p, fact_ids)
        if embs is None or embs.shape[0] == 0:
            cohesion = 0.0
        else:
            cohesion = _cohesion_score(embs)
        if cohesion < float(min_cohesion):
            continue
        score = cohesion * len(fact_ids) * purity
        entry = {
            "community_id": str(c.get("id", "")),
            "size": len(fact_ids),
            "fact_ids": fact_ids,
            "suggested_skill_name": _suggest_skill_name(topic_counts),
            "dominant_topic": str(top_topic),
            "topic_purity": float(purity),
            "cohesion": float(cohesion),
            "emergence_score": float(score),
        }
        if "from_master" in c:
            entry["from_master"] = bool(c["from_master"])
        if "from_hybrid" in c:
            entry["from_hybrid"] = bool(c["from_hybrid"])
        out.append(entry)
    out.sort(key=lambda d: -d["emergence_score"])
    return out[: int(max_n)]


__all__ = ["detect_emerging_skills"]
