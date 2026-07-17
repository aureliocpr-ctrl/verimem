"""Populate the entity KG from the facts corpus (entity-live, step 2).

The missing wiring the README declared honestly: entity_kg.py + PPR were
"plumbing-complete, not data-complete" — no extraction ran over the
corpus, so entity retrieval returned 0 hits on real data. This module
walks the alive facts, extracts entities (zero-API lite tier by
default), upserts them, links fact<->entity and wires per-fact
co-occurrence edges — the HippoRAG-style signal Personalized PageRank
walks on.

Idempotent end-to-end: EntityStore.store dedups on name_norm,
link_fact has a (fact_id, entity_id) PK, add_edge is INSERT OR IGNORE.
Re-running converges, never duplicates.
"""
from __future__ import annotations

import sqlite3
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .entity_extract_lite import extract_entities_lite
from .entity_kg import Entity, EntityStore
from .flow_events import emit_flow as _emit_flow

#: co-occurrence pairs are wired between the FIRST N entities of a fact —
#: bounds the per-fact clique to N*(N-1)/2 edges (8 -> 28).
MAX_COOCCUR_ENTITIES = 8


def entity_kg_path_for(semantic_db: Path | str) -> Path:
    """Derive the sibling entity-KG path from a semantic.db path.

    Mirrors the live layout (<data_dir>/semantic/semantic.db ↔
    <data_dir>/entity_kg/entity_kg.db) and, crucially, keeps tests
    hermetic: a tmp-dir semantic.db derives a tmp-dir KG, never the
    global CONFIG.data_dir one. Same sibling-derivation pattern as
    community_detector._sibling_episodes_db.
    """
    parent = Path(semantic_db).resolve().parent
    root = parent.parent if parent.name == "semantic" else parent
    return root / "entity_kg" / "entity_kg.db"


def populate_entities_for_fact(
    fact_id: str,
    proposition: str,
    kg: EntityStore,
    *,
    extract_fn: Callable[[str], list[dict[str, str]]] | None = None,
    entities: list[dict[str, str]] | None = None,
) -> tuple[int, int]:
    """Single-fact populate: extract → upsert → link → co-occur edges.

    The unit of work `populate_entity_graph` loops over, factored out so
    the live write path (SemanticMemory.store) can ingest one fact at a
    time. Returns (entities_linked, edges_wired). Idempotent: store
    dedups on name_norm, link_fact has a (fact_id, entity_id) PK,
    add_edge is INSERT OR IGNORE.

    ``entities`` lets a caller that already extracted (e.g. the store()
    hook's lazy-skip check) avoid a second regex pass. The whole ingest
    runs inside ONE kg.session() — the per-call connection pattern was
    ~76 opens per fact (122 ms/store; broke the CI anti-hang guard).
    """
    if entities is None:
        extract = extract_fn or extract_entities_lite
        entities = extract(proposition or "")
    if not entities:
        return (0, 0)
    eids: list[str] = []
    created: list[dict[str, str]] = []
    linked = 0
    edges = 0
    with kg.session():
        for e in entities:
            ent = Entity(canonical_name=e["name"], type=e.get("type", ""))
            eid = kg.store(ent)
            # store() returns the EXISTING id on a name_norm hit and the new
            # object's id otherwise — that identity is how we tell a node
            # being BORN from one being touched again, with no extra query.
            if eid == ent.id:
                created.append({"id": eid, "name": ent.canonical_name,
                                "type": ent.type})
            kg.link_fact(str(fact_id), eid)
            eids.append(eid)
            linked += 1
        # Co-occurrence clique (bounded) — the edges PPR walks on.
        head = eids[:MAX_COOCCUR_ENTITIES]
        for i in range(len(head)):
            for j in range(i + 1, len(head)):
                kg.add_edge(head[i], head[j], "co_occurs",
                            weight=1.0, source_fact_id=str(fact_id))
                kg.add_edge(head[j], head[i], "co_occurs",
                            weight=1.0, source_fact_id=str(fact_id))
                edges += 2
    # The graph's life, observable: which nodes were BORN and which lit up.
    # Flow metadata only (names + ids), never the fact's text.
    _emit_flow("flow.entity", fact_id=str(fact_id), created=created,
               touched=eids, edges=edges)
    return (linked, edges)


def populate_entity_graph(
    semantic_db: Path | str,
    kg: EntityStore,
    *,
    extract_fn: Callable[[str], list[dict[str, str]]] | None = None,
    limit: int | None = None,
    statuses_excluded: tuple[str, ...] = ("orphaned", "quarantined"),
) -> dict[str, Any]:
    """Walk alive facts, extract entities, link + wire co-occurrence.

    Args:
        semantic_db: path to semantic.db (opened read-only).
        kg: target EntityStore (its own db).
        extract_fn: text -> [{"name","type"}]; defaults to the
            deterministic zero-API lite extractor.
        limit: cap on facts processed (None = all alive facts).
        statuses_excluded: fact statuses never ingested.

    Returns stats: {facts_scanned, facts_with_entities, entities_linked,
    edges_wired, elapsed_s}. Never raises on a single bad fact — one
    malformed row must not kill a 4k-fact backfill.
    """
    extract = extract_fn or extract_entities_lite
    t0 = time.time()
    placeholders = ",".join("?" for _ in statuses_excluded)
    conn = sqlite3.connect(f"file:{semantic_db}?mode=ro", uri=True,
                           timeout=10)
    try:
        sql = (
            "SELECT id, proposition FROM facts WHERE superseded_by IS NULL "
            f"AND (status IS NULL OR status NOT IN ({placeholders})) "
            "ORDER BY created_at"
        )
        if limit is not None:
            sql += f" LIMIT {int(limit)}"
        rows = conn.execute(sql, statuses_excluded).fetchall()
    finally:
        conn.close()

    facts_with = 0
    linked = 0
    edges = 0
    for fact_id, prop in rows:
        try:
            f_linked, f_edges = populate_entities_for_fact(
                str(fact_id), prop or "", kg, extract_fn=extract,
            )
            if f_linked == 0:
                continue
            facts_with += 1
            linked += f_linked
            edges += f_edges
        except Exception:  # noqa: BLE001 — one bad fact must not kill a backfill
            continue

    return {
        "facts_scanned": len(rows),
        "facts_with_entities": facts_with,
        "entities_linked": linked,
        "edges_wired": edges,
        "entities_total": kg.count(),
        "elapsed_s": round(time.time() - t0, 2),
    }


__all__ = [
    "populate_entity_graph",
    "populate_entities_for_fact",
    "entity_kg_path_for",
    "MAX_COOCCUR_ENTITIES",
]
