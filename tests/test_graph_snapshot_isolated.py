"""Il GRAFO deve essere un grafo, non una nuvola di punti.

Bug riportato da Aurelio 2026-07-15 ("il grafo è sconclusionato e
graficamente matto"), causa misurata sullo store reale via /v1/graph:
300 nodi / 600 archi ma **194 nodi (65%) senza NEMMENO un arco** — la
policy "riempi il budget nodi avanzato con le entità rimanenti (anche
isolate)" produceva due terzi di puntini muti attorno a un ammasso.

Contratto nuovo: ``snapshot()`` rende il sottografo CONNESSO (solo nodi
che un arco tocca); le entità isolate restano contabilizzate in
``isolated_count`` — dichiarate, non disegnate — e tornano solo su
richiesta esplicita (``include_isolated=True``, per chi ispeziona il
corpus e non la struttura).
"""
from __future__ import annotations

from engram.entity_kg import Entity, EntityStore


def _store(tmp_path):
    return EntityStore(db_path=tmp_path / "kg.db")


def _seed(kg):
    """3 entità connesse (a→b→c) + 4 isolate."""
    a = kg.store(Entity(canonical_name="alpha", type="concept"))
    b = kg.store(Entity(canonical_name="beta", type="concept"))
    c = kg.store(Entity(canonical_name="gamma", type="concept"))
    kg.add_edge(a, b, "relates_to", source_fact_id="f1")
    kg.add_edge(b, c, "relates_to", source_fact_id="f2")
    for n in ("lonely1", "lonely2", "lonely3", "lonely4"):
        kg.store(Entity(canonical_name=n, type="concept"))
    return {a, b, c}


def test_snapshot_returns_only_connected_nodes(tmp_path):
    kg = _store(tmp_path)
    connected = _seed(kg)
    snap = kg.snapshot()
    ids = {n["id"] for n in snap["nodes"]}
    assert ids == connected, "solo i nodi toccati da un arco vengono disegnati"
    assert len(snap["edges"]) == 2


def test_snapshot_declares_isolated_count(tmp_path):
    """Le entità isolate non spariscono dalla verità: sono DICHIARATE."""
    kg = _store(tmp_path)
    _seed(kg)
    snap = kg.snapshot()
    assert snap["isolated_count"] == 4


def test_snapshot_include_isolated_opt_in(tmp_path):
    kg = _store(tmp_path)
    _seed(kg)
    snap = kg.snapshot(include_isolated=True)
    names = {n["name"] for n in snap["nodes"]}
    assert {"lonely1", "lonely2", "lonely3", "lonely4"} <= names
    assert len(snap["nodes"]) == 7


def test_empty_graph_has_zero_isolated(tmp_path):
    kg = _store(tmp_path)
    snap = kg.snapshot()
    assert snap["nodes"] == [] and snap["edges"] == []
    assert snap["isolated_count"] == 0


def test_isolated_only_store_draws_nothing_but_counts(tmp_path):
    """Nessun arco: il grafo è VUOTO (onesto), non 300 puntini."""
    kg = _store(tmp_path)
    for n in ("x", "y", "z"):
        kg.store(Entity(canonical_name=n, type="concept"))
    snap = kg.snapshot()
    assert snap["nodes"] == []
    assert snap["isolated_count"] == 3
