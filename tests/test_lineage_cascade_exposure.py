"""TDD for the narrative-descendant exposure analysis (pure graph over real-shaped facts).

R26: this measures the lineage_to NARRATIVE graph (an upper bound), NOT logical
justification-debt — see the module docstring.
"""
from __future__ import annotations

from benchmark.lineage_cascade_exposure import _reverse_graph, run, transitive_dependents


def _f(i: str, deps=()):  # duck-typed fact dict; lineage_to = the narrative successor field
    return {"id": i, "proposition": f"prop {i}", "verified_by": "e", "lineage_to": list(deps)}


_GRAPH = [_f("F0"), _f("D1", ["F0"]), _f("D2", ["F0"]), _f("D3", ["D1"]),
          _f("V1"), _f("V2")]


def test_transitive_dependents_chain() -> None:
    rev = _reverse_graph(_GRAPH)
    assert transitive_dependents("F0", rev) == {"D1", "D2", "D3"}
    assert transitive_dependents("D1", rev) == {"D3"}
    assert transitive_dependents("V1", rev) == set()


def test_reverse_graph_drops_dangling_edges() -> None:
    rev = _reverse_graph([_f("A", ["ghost"]), _f("B", ["A"])])
    assert "ghost" not in rev          # edge to a non-present fact is dangling, dropped
    assert rev["A"] == {"B"}


def test_run_reports_narrative_exposure() -> None:
    r = run(_GRAPH)
    assert r["n_foundations_with_narrative_successors"] == 2   # F0 and D1 have successors
    assert r["max_narrative_cascade"] == 3                      # F0 -> D1,D2,D3
    assert r["top_foundations"][0]["id"] == "F0"
    assert "NARRATIVE" in r["edge_semantics"]                   # honest labelling (R26)
