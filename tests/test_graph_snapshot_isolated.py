"""Il GRAFO: una finestra ONESTA sul presente, non un fossile.

Tre bug veri, trovati guardando lo store reale di Aurelio (2026-07-15):

1. "sconclusionato e graficamente matto" — 300 nodi / 600 archi con 194 nodi
   (65%) senza un arco, mescolati ai connessi come puntini muti.
2. Nascondere gli isolati (primo tentativo) — RIGETTATO: "voglio vedere tutti
   i nodi, i nodi reali".
3. LA CAUSA VERA, sotto le prime due: il campionamento prendeva i 600 archi
   ``ORDER BY created_at ASC`` su **78.713** — lo 0,76%, e i più VECCHI. Il
   grafo era un fossile della prima sessione: i nodi nuovi non comparivano
   MAI (i loro archi sono i più recenti = sempre tagliati), e quei "194
   isolati" erano una BUGIA — entità con archi veri, fuori dal campione.

Contratto: la finestra guarda il PRESENTE (entità più recenti), porta gli
archi VERI fra i nodi che mostra, e ogni nodo dichiara il suo ``degree``
REALE (contato su tutto il DB, non sul campione) — così ``isolated`` significa
"non ha davvero relazioni", non "il campione le ha buttate". I totali
(``total_entities``/``total_edges``) sono dichiarati: una finestra che non
dice di essere una finestra mente.
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


def test_snapshot_draws_every_real_node(tmp_path):
    kg = _store(tmp_path)
    _seed(kg)
    snap = kg.snapshot()
    names = {n["name"] for n in snap["nodes"]}
    assert names == {"alpha", "beta", "gamma",
                     "lonely1", "lonely2", "lonely3", "lonely4"}
    assert len(snap["edges"]) == 2


def test_every_node_declares_isolated_and_real_degree(tmp_path):
    kg = _store(tmp_path)
    connected = _seed(kg)
    snap = kg.snapshot()
    by_name = {n["name"]: n for n in snap["nodes"]}
    assert by_name["beta"]["degree"] == 2
    assert by_name["alpha"]["degree"] == 1
    assert by_name["beta"]["isolated"] is False
    assert by_name["lonely1"]["isolated"] is True
    assert by_name["lonely1"]["degree"] == 0
    assert {n["id"] for n in snap["nodes"] if not n["isolated"]} == connected


def test_a_brand_new_node_is_in_the_window(tmp_path):
    """Il bug del fossile: un nodo appena nato DEVE comparire, anche quando
    il grafo è pieno di storia più vecchia."""
    kg = _store(tmp_path)
    for i in range(40):                      # storia
        old = kg.store(Entity(canonical_name=f"old{i}", type="concept"))
        kg.add_edge(old, old, "self", source_fact_id=f"f{i}")
    fresh_a = kg.store(Entity(canonical_name="Thalassa Robotics", type="org"))
    fresh_b = kg.store(Entity(canonical_name="Trondheim", type="place"))
    kg.add_edge(fresh_a, fresh_b, "co_occurs", source_fact_id="new")

    snap = kg.snapshot(max_nodes=10, max_edges=10)
    names = {n["name"] for n in snap["nodes"]}
    assert "Thalassa Robotics" in names, "il nuovo non deve MAI essere invisibile"
    assert "Trondheim" in names
    pairs = {(e["src"], e["dst"]) for e in snap["edges"]}
    assert (fresh_a, fresh_b) in pairs, "e porta con sé il suo arco vero"


def test_edges_are_real_between_shown_nodes(tmp_path):
    """Ogni arco mostrato ha entrambi i capi nella finestra: nessun arco
    fantasma verso nodi che non si vedono."""
    kg = _store(tmp_path)
    for i in range(30):
        a = kg.store(Entity(canonical_name=f"n{i}", type="c"))
        b = kg.store(Entity(canonical_name=f"m{i}", type="c"))
        kg.add_edge(a, b, "co_occurs", source_fact_id=f"f{i}")
    snap = kg.snapshot(max_nodes=12, max_edges=50)
    ids = {n["id"] for n in snap["nodes"]}
    for e in snap["edges"]:
        assert e["src"] in ids and e["dst"] in ids


def test_window_declares_the_totals(tmp_path):
    """Una finestra che non dichiara di essere una finestra mente."""
    kg = _store(tmp_path)
    _seed(kg)
    snap = kg.snapshot(max_nodes=3)
    assert snap["total_entities"] == 7
    assert snap["total_edges"] == 2
    assert len(snap["nodes"]) == 3
    assert snap["isolated_count"] == 4       # sul DB intero, non sul campione


def test_empty_graph(tmp_path):
    snap = _store(tmp_path).snapshot()
    assert snap["nodes"] == [] and snap["edges"] == []
    assert snap["isolated_count"] == 0
    assert snap["total_entities"] == 0


def test_isolated_only_store_draws_them_all(tmp_path):
    kg = _store(tmp_path)
    for n in ("x", "y", "z"):
        kg.store(Entity(canonical_name=n, type="concept"))
    snap = kg.snapshot()
    assert len(snap["nodes"]) == 3
    assert all(n["isolated"] for n in snap["nodes"])
    assert snap["isolated_count"] == 3
