"""Query-auto-seeded entity-PPR fact ranklist (competitor-gap step 2a, 2026-06-14).

HippoRAG-2's edge is auto-seeded persistent-graph PPR as a primary ranker. Engram
already has the entity graph + PPR + PPR-mass fact ranking, but gated it behind
caller-supplied entity ids (hippo_ppr_retrieve requires `query_entities`). This leaf
building block closes the SEEDING gap: extract entities from a free-text QUERY,
resolve them to entity ids, run PPR, and return the PPR-mass-ranked fact ids — so a
gold fact the bi-encoder misses (cosine ~0) but that shares an entity with the query
can still be surfaced (the documented ~30% wording-mismatch / multi-hop residual).

Fail-soft by contract: returns [] on no query / no store / no resolvable entities /
any error, so a caller (the future RRF fusion in recall) degrades cleanly to pure
cosine. Pure given the store; the RRF fusion + CE-rerank wiring is a SEPARATE step
(2b) so this can be tested and reviewed in isolation before touching live recall.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .multi_signal_fusion import rrf_fuse


def _fact_id_of(x: Any) -> str | None:
    """Extract a fact id from a facts_ranked entry, tolerant to its shape
    (str | {'fact_id'|'id': ...} | (fact_id, score) | obj.fact_id/.id)."""
    if isinstance(x, str):
        return x or None
    if isinstance(x, dict):
        return x.get("fact_id") or x.get("id")
    if isinstance(x, (tuple, list)) and x:
        return _fact_id_of(x[0])
    return getattr(x, "fact_id", None) or getattr(x, "id", None)


def ppr_seeded_fact_ids(
    query: str | None, entity_store: Any, *, max_seeds: int = 8, k_facts: int = 20,
) -> list[str]:
    """Auto-seed entity-PPR from a free-text ``query`` → ranked fact-id list.

    Pipeline: ``extract_entities_lite(query)`` → ``EntityStore.get_by_name`` →
    ``EntityStore.ppr(seeds).facts_ranked``. Returns the PPR-mass-ranked fact ids,
    or ``[]`` (fail-soft) on no entities / no store / any error.
    """
    if not query or entity_store is None:
        return []
    try:
        from .entity_extract_lite import extract_entities_lite

        ents = extract_entities_lite(query)
        seeds: list[str] = []
        seen: set[str] = set()
        for e in ents:
            name = e.get("name") if isinstance(e, dict) else None
            if not name:
                continue
            ent = entity_store.get_by_name(name)
            ent_id = getattr(ent, "id", None) if ent is not None else None
            if ent_id and ent_id not in seen:
                seen.add(ent_id)
                seeds.append(ent_id)
            if len(seeds) >= max_seeds:
                break
        if not seeds:
            return []
        res = entity_store.ppr(seeds, k_facts=k_facts)
        ranked = (res or {}).get("facts_ranked") or []
        out: list[str] = []
        for x in ranked:
            fid = _fact_id_of(x)
            if fid:
                out.append(fid)
        return out
    except Exception:  # noqa: BLE001 — fail-soft; recall degrades to pure cosine
        return []


def fuse_dense_and_ppr(
    dense_hits: list[tuple[Any, float]],
    extra_ranklists: list[list[str]],
    fetch_fact: Callable[[str], Any],
    *,
    k: float = 60.0,
) -> list[tuple[Any, float]]:
    """RRF-fuse a dense ``(Fact, sim)`` hit list with N extra fact-id ranklists
    (entity-PPR, BM25-lexical, …) — pure, no SemanticMemory dependency.

    Returns a reordered candidate pool of ``(Fact, sim)``: dense facts keep their
    cosine sim; extra-only facts (reached via a graph or lexical signal even at
    cosine ~0) are fetched via ``fetch_fact`` and added with ``sim=0.0`` so they
    ENTER the pool the downstream CE-rerank then re-scores — rescuing the
    bi-encoder's wording-mismatch / exact-token / multi-hop misses (the HippoRAG-2
    + Zep gaps). Each extra list is its OWN RRF signal (not concatenated), so a
    rank-1 BM25 hit and a rank-1 PPR hit both get full weight.

    Fail-soft: no extra ids → the dense list is returned unchanged; a failing
    ``fetch_fact`` for one id is skipped, never raised.
    """
    extra = [lst for lst in extra_ranklists if lst]
    if not extra:
        return list(dense_hits)
    by_id: dict[str, tuple[Any, float]] = {}
    dense_ids: list[str] = []
    for f, sim in dense_hits:
        fid = getattr(f, "id", None)
        if fid:
            by_id[fid] = (f, sim)
            dense_ids.append(fid)
    fused = rrf_fuse([dense_ids, *extra], k=k)  # [(id, score)] sorted DESC
    out: list[tuple[Any, float]] = []
    seen: set[str] = set()
    for fid, _score in fused:
        if fid in by_id:
            out.append(by_id[fid])
            seen.add(fid)
        else:
            try:
                f = fetch_fact(fid)
            except Exception:  # noqa: BLE001 — one bad fetch must not break recall
                f = None
            if f is not None:
                out.append((f, 0.0))
                seen.add(fid)
    # Defensive: keep any dense hit the fusion somehow dropped (id-less rows).
    for f, sim in dense_hits:
        if getattr(f, "id", None) not in seen:
            out.append((f, sim))
    return out


__all__ = ["ppr_seeded_fact_ids", "fuse_dense_and_ppr"]
