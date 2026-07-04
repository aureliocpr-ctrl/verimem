"""EntityStore PPR graph cache (competitor-gap step 1, 2026-06-14).

ppr/ppr_weighted rebuilt the full nx.DiGraph from entity_edges on EVERY call — the
exact cost that kept the HippoRAG-class entity-PPR signal out of hot recall. The
graph is now cached and invalidated by a cross-process PRAGMA data_version probe
(mirror of Semantic/EpisodicMemory): reads reuse it; an edge commit (same instance
OR another process) forces a rebuild.
"""
from __future__ import annotations

from engram.entity_kg import Entity, EntityStore


def _mk(es, name):
    return es.store(Entity(canonical_name=name, type="concept"))


def test_graph_is_cached_and_rebuilt_on_own_edge(tmp_path):
    es = EntityStore(db_path=tmp_path / "ekg.db")
    g1 = es._get_graph()
    g2 = es._get_graph()
    assert g1 is g2, "consecutive reads must reuse the cached graph object"

    a, b = _mk(es, "Alpha"), _mk(es, "Beta")
    es.add_edge(a, b, "rel", weight=1.0)  # commit bumps data_version
    g3 = es._get_graph()
    assert g3 is not g1, "an edge commit must invalidate + rebuild the cache"
    assert g3.has_edge(a, b)


def test_graph_sees_cross_instance_edge(tmp_path):
    db = tmp_path / "ekg.db"
    es1 = EntityStore(db_path=db)
    es1._get_graph()  # build (empty) + stamp data_version on es1

    es2 = EntityStore(db_path=db)  # a second "process"
    x, y = _mk(es2, "Xeno"), _mk(es2, "Yotta")
    es2.add_edge(x, y, "rel", weight=1.0)

    g = es1._get_graph()  # es1's cache is stale; the dv probe catches es2's commit
    assert g.has_edge(x, y), "cross-instance edge must invalidate es1's cache"


def test_ppr_still_ranks_after_caching(tmp_path):
    """Regression: the cached graph yields a working PPR result (not broken)."""
    es = EntityStore(db_path=tmp_path / "ekg.db")
    a, b, c = _mk(es, "Aa"), _mk(es, "Bb"), _mk(es, "Cc")
    es.add_edge(a, b, "rel", weight=1.0)
    es.add_edge(b, c, "rel", weight=1.0)
    out = es.ppr([a])
    assert out["graph_size"]["nodes"] >= 3 and out["graph_size"]["edges"] >= 2
    assert len(out["ranked"]) >= 3, "all entities ranked by PPR over the cached graph"
    out2 = es.ppr([a])  # cached graph reused → identical structure, no crash
    assert out2["graph_size"] == out["graph_size"]
