"""R25: Memory compaction — detect near-duplicate facts.

Greedy clustering by Jaccard similarity on propositions. Each
cluster (size >= 2) is reported with representative + duplicate
ids. Caller can prune dupes or merge into one consolidated fact.

Pure-local, no LLM.
"""
from __future__ import annotations

import re
from typing import Any

_TOKEN_RE = re.compile(r"[A-Za-z0-9_\-]+")


def _tokens(text: str) -> set[str]:
    return {t.lower() for t in _TOKEN_RE.findall(text or "")}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def find_duplicates(
    facts: list[Any],
    *,
    sim_threshold: float = 0.7,
    top_k: int = 100,
) -> dict[str, Any]:
    """Return clusters of near-duplicate facts."""
    if not facts:
        return {
            "duplicate_clusters": [],
            "n_facts_scanned": 0,
            "n_duplicate_pairs": 0,
        }

    clusters: list[list[tuple[Any, float]]] = []
    for f in facts:
        f_tokens = _tokens(getattr(f, "proposition", ""))
        if not f_tokens:
            continue
        placed = False
        best_sim = 0.0
        for cl in clusters:
            sample = cl[0][0]
            s_tokens = _tokens(getattr(sample, "proposition", ""))
            sim = _jaccard(f_tokens, s_tokens)
            if sim >= sim_threshold:
                cl.append((f, sim))
                placed = True
                best_sim = max(best_sim, sim)
                break
        if not placed:
            clusters.append([(f, 1.0)])

    # Build output for clusters of size >=2
    out_clusters: list[dict[str, Any]] = []
    n_pairs = 0
    for cl in clusters:
        if len(cl) < 2:
            continue
        rep = cl[0][0]
        ids = [getattr(item[0], "id", "") for item in cl]
        max_sim = max(item[1] for item in cl if item[1] < 1.0) if any(item[1] < 1.0 for item in cl) else 1.0
        out_clusters.append({
            "representative_id": getattr(rep, "id", ""),
            "representative_proposition": (
                getattr(rep, "proposition", "")[:120]
            ),
            "fact_ids": ids,
            "n_dupes": len(cl),
            "max_similarity": round(max_sim, 3),
        })
        n_pairs += len(cl) - 1  # each extra is a "duplicate pair" with rep

    out_clusters.sort(key=lambda c: -c["n_dupes"])

    return {
        "duplicate_clusters": out_clusters[:top_k],
        "n_facts_scanned": len(facts),
        "n_duplicate_pairs": n_pairs,
    }


__all__ = ["find_duplicates"]
