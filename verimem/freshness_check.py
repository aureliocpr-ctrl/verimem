"""Cycle #82 — facts freshness check + auto-supersede candidate finder.

Generalized lesson from NEXUS BUG#1 (kev-feed obsoleto, fact e389a03e2a58):
any topic namespace accumulates measurements over time, and older facts
go silently stale. Manually inspecting 800 facts is unfeasible. This
tool surfaces:

  - "stale" facts: created_at older than threshold_days AND not
    already explicitly superseded
  - "auto-supersede candidates": stale fact + newer fact under same
    topic_glob with embedding cosine similarity >= sim_threshold

The user reviews candidates and applies `hippo_fact_supersede` or
`hippo_fact_supersede_chain` to commit.

Pure-local, no LLM.
"""
from __future__ import annotations

import time
from typing import Any

import numpy as np

from . import embedding


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def facts_freshness_check(
    semantic: Any, topic_glob: str, *,
    threshold_days: float = 30.0,
    sim_threshold: float = 0.85,
    max_results: int = 50,
) -> dict[str, Any]:
    """Cycle #82 (2026-05-16) — surface stale facts and propose
    auto-supersede candidates.

    Args:
        semantic: SemanticMemory-like (or any agent.semantic; we only
            call summary_topic + read embeddings via memory access).
        topic_glob: ``project/X/*`` or any glob accepted by
            ``summary_topic``.
        threshold_days: facts older than this are flagged stale
            (unless already superseded — only live facts considered).
        sim_threshold: minimum embedding cosine similarity to pair a
            stale fact with a newer one as auto-supersede candidate.
        max_results: cap on the ``stale`` list returned. Counts always
            accurate via ``n_stale``.

    Returns:
        dict with topic_glob, threshold_days, sim_threshold, n_scanned,
        n_stale, n_auto_supersede_candidates, stale (list capped),
        candidates (list).
    """
    summary = semantic.summary_topic(topic_glob, max_facts=10_000)
    live = [f for f in summary["facts"] if f.get("superseded_by") is None]
    n_scanned = len(live)
    now = time.time()
    day = 86400.0

    # Stale = live + older than threshold_days
    stale_facts: list[dict[str, Any]] = []
    for f in live:
        age_days = max(0.0, (now - float(f["created_at"])) / day)
        if age_days > threshold_days:
            stale_facts.append({
                "id": f["id"],
                "topic": f["topic"],
                "created_at": f["created_at"],
                "age_days": age_days,
                "proposition": (f.get("proposition") or "")[:120],
            })

    # Sort stale newest-first for stability (oldest at end). Cap for
    # display; counts stay accurate.
    stale_facts.sort(key=lambda s: -s["created_at"])
    stale_display = stale_facts[:max(0, int(max_results))]

    # Auto-supersede candidates (cycle #87 perf: per-topic vectorized
    # cosine matrix). Group stale + live by topic, stack embeddings
    # once per topic, then compute (n_stale_in_topic x n_newer_in_topic)
    # cosine matrix in one numpy call. Pre-fix: Python loop scaled
    # O(stale x neighbours) → 2.3s on 10k corpus. Post-fix: vector
    # cosine + topic groupby drops it by ~5-10x.
    candidates: list[dict[str, Any]] = []
    if stale_facts and sim_threshold > 0:
        # Group by topic
        live_by_topic: dict[str, list[dict[str, Any]]] = {}
        for f in live:
            live_by_topic.setdefault(f["topic"], []).append(f)
        stale_by_topic: dict[str, list[dict[str, Any]]] = {}
        for s in stale_facts:
            stale_by_topic.setdefault(s["topic"], []).append(s)
        # Bulk-load embeddings once
        ids_of_interest = {f["id"] for f in stale_facts} | {f["id"] for f in live}
        emb_map = _bulk_load_embeddings(semantic, ids_of_interest)

        for topic, stale_grp in stale_by_topic.items():
            same_topic = live_by_topic.get(topic, [])
            if not same_topic or not stale_grp:
                continue
            # Stack newer-candidate embeddings (filtered by id != stale,
            # but cheaper to keep all then mask per-stale). Skip facts
            # whose embedding is missing.
            cand_pool = [c for c in same_topic if c["id"] in emb_map]
            stale_pool = [s for s in stale_grp if s["id"] in emb_map]
            if not cand_pool or not stale_pool:
                continue
            cand_embs = np.stack([emb_map[c["id"]] for c in cand_pool])
            stale_embs = np.stack([emb_map[s["id"]] for s in stale_pool])
            # Vectorized cosine matrix (n_stale x n_cand)
            # Normalize once
            cand_norms = np.linalg.norm(cand_embs, axis=1, keepdims=True)
            cand_norms[cand_norms == 0] = 1.0
            cand_unit = cand_embs / cand_norms
            stale_norms = np.linalg.norm(stale_embs, axis=1, keepdims=True)
            stale_norms[stale_norms == 0] = 1.0
            stale_unit = stale_embs / stale_norms
            sim_matrix = stale_unit @ cand_unit.T  # (n_stale, n_cand)

            cand_created = np.array([float(c["created_at"]) for c in cand_pool])
            for i, stale in enumerate(stale_pool):
                stale_id = stale["id"]
                stale_ts = float(stale["created_at"])
                # Mask: cand must be strictly newer + not self
                row = sim_matrix[i].copy()
                for j, cand in enumerate(cand_pool):
                    if cand["id"] == stale_id or cand_created[j] <= stale_ts:
                        row[j] = -1.0
                best_j = int(np.argmax(row))
                best_sim = float(row[best_j])
                if best_sim >= sim_threshold:
                    cand = cand_pool[best_j]
                    candidates.append({
                        "old_id": stale_id,
                        "new_id": cand["id"],
                        "similarity": best_sim,
                        "old_age_days": stale["age_days"],
                        "old_topic": stale["topic"],
                        "new_topic": cand["topic"],
                    })

    return {
        "topic_glob": topic_glob,
        "threshold_days": threshold_days,
        "sim_threshold": sim_threshold,
        "n_scanned": n_scanned,
        "n_stale": len(stale_facts),
        "n_auto_supersede_candidates": len(candidates),
        "stale": stale_display,
        "candidates": candidates,
    }


def _bulk_load_embeddings(semantic: Any, ids: set[str]) -> dict[str, np.ndarray]:
    """Fetch raw embedding BLOB for a set of fact ids in one SQL pass."""
    if not ids:
        return {}
    placeholders = ",".join("?" for _ in ids)
    with semantic._connect() as conn:
        rows = conn.execute(
            f"SELECT id, embedding FROM facts WHERE id IN ({placeholders})",
            tuple(ids),
        ).fetchall()
    out: dict[str, np.ndarray] = {}
    for r in rows:
        try:
            out[r["id"]] = embedding.deserialize(r["embedding"])
        except Exception:
            continue
    return out


__all__ = ["facts_freshness_check"]
