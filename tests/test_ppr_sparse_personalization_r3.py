"""Audit 3-round #9 (perf/correctness): PPR must seed a SPARSE personalization
vector (only the query entities) and use tol=1e-6, not a dense O(nodes) dict
rebuilt on every call with tol=1e-9.

ppr()/ppr_weighted() built ``{n: 0.0 for n in graph.nodes}`` on every call — an
O(N) allocation over the FULL entity graph (thousands of nodes) per query — then
set the few seeds. networkx treats missing nodes as 0.0, so a sparse
``{seed: mass}`` dict is mathematically identical but avoids the per-call O(N)
build. The docstring already promised tol=1e-6 while the code used 1e-9 (extra
power-iterations with no ranking benefit). The fix threads a sparse dict +
tol=1e-6 into both call sites.
"""
from __future__ import annotations

import networkx as nx
import pytest

from engram.entity_kg import Entity, EntityStore


@pytest.fixture
def store(tmp_path):
    return EntityStore(db_path=tmp_path / "kg.db")


def _chain(store: EntityStore, n: int = 6) -> list[str]:
    ids = [store.store(Entity(canonical_name=f"e{i}", type="x")) for i in range(n)]
    for i in range(n - 1):
        store.add_edge(ids[i], ids[i + 1], "rel", weight=1.0)
    return ids


def _spy_pagerank(monkeypatch, captured: dict) -> None:
    real = nx.pagerank

    def spy(graph, **kw):
        captured["personalization"] = kw.get("personalization")
        captured["tol"] = kw.get("tol")
        captured["n_nodes"] = graph.number_of_nodes()
        return real(graph, **kw)

    monkeypatch.setattr("engram.entity_kg.nx.pagerank", spy)


def test_ppr_personalization_is_sparse_and_tol_1e6(store, monkeypatch) -> None:
    ids = _chain(store, 6)
    captured: dict = {}
    _spy_pagerank(monkeypatch, captured)
    store.ppr([ids[0]], k=3)
    assert captured["n_nodes"] == 6, "precondition: il grafo pieno ha 6 nodi"
    assert len(captured["personalization"]) == 1, \
        "personalization deve essere sparse (solo i seed), non O(nodi)"
    assert captured["tol"] == pytest.approx(1e-6), \
        "tol deve essere 1e-6 (come il docstring), non 1e-9"


def test_ppr_weighted_personalization_is_sparse_and_tol_1e6(
    store, monkeypatch,
) -> None:
    ids = _chain(store, 6)
    captured: dict = {}
    _spy_pagerank(monkeypatch, captured)
    store.ppr_weighted({ids[0]: 1.0}, k=3)
    assert len(captured["personalization"]) == 1, \
        "ppr_weighted: personalization sparse (solo i seed pesati)"
    assert captured["tol"] == pytest.approx(1e-6)


def test_ppr_seed_dominates_ranking(store) -> None:
    """Equivalence guard: sparse personalization must not change the semantics —
    the personalized seed still dominates the PPR ranking (networkx assigns 0 to
    the omitted nodes, identical to the old dense zero-fill)."""
    ids = _chain(store, 6)
    res = store.ppr([ids[0]], k=6)
    assert res["ranked"][0]["entity_id"] == ids[0], \
        "il seed personalizzato resta in cima al ranking PPR"
