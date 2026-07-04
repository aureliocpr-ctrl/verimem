"""R30: Fact chaining — multi-hop reasoning across natural-language facts.

BFS from a seed query token-set. At each depth layer, find facts
whose proposition overlaps significantly with the "frontier" of
already-included tokens. Limit by max_depth.

Distinct from forward_chain (R8) which requires rule-shaped facts.
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


def chain_facts(
    *,
    seed_query: str,
    facts: list[Any],
    max_depth: int = 3,
    min_overlap: float = 0.15,
    max_per_depth: int = 5,
) -> dict[str, Any]:
    """BFS-chain facts starting from seed_query tokens."""
    if not seed_query or not facts:
        return {
            "chain": [],
            "max_depth_reached": 0,
            "n_facts_scanned": len(facts),
        }

    fact_tokens_map = {
        getattr(f, "id", ""): (f, _tokens(getattr(f, "proposition", "")))
        for f in facts
    }
    frontier = _tokens(seed_query)
    visited: set[str] = set()
    chain: list[dict[str, Any]] = []
    depth_reached = 0

    for depth in range(1, max_depth + 1):
        candidates: list[tuple[float, str, Any]] = []
        for fid, (f, ftoks) in fact_tokens_map.items():
            if fid in visited:
                continue
            sim = _jaccard(frontier, ftoks)
            if sim >= min_overlap:
                candidates.append((sim, fid, f))
        candidates.sort(key=lambda c: -c[0])
        layer_added: list[Any] = []
        for sim, fid, f in candidates[:max_per_depth]:
            chain.append({
                "id": fid,
                "proposition": getattr(f, "proposition", "")[:120],
                "depth": depth,
                "similarity": round(sim, 3),
            })
            visited.add(fid)
            layer_added.append(f)
            depth_reached = max(depth_reached, depth)
        if not layer_added:
            break
        # Extend frontier with new tokens for next hop
        for f in layer_added:
            frontier = frontier | fact_tokens_map[getattr(f, "id", "")][1]

    return {
        "chain": chain,
        "max_depth_reached": depth_reached,
        "n_facts_scanned": len(facts),
    }


__all__ = ["chain_facts"]
