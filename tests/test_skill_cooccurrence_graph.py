"""R36: Build skill co-occurrence graph.

Adjacency map: skill_id → [list of skills it co-occurs with].
Edge weights = co-occurrence count.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class _Ep:
    id: str
    skills_used: list[str] = field(default_factory=list)


def test_empty_returns_empty_graph():
    from engram.skill_cooccurrence_graph import build_cooccurrence_graph
    out = build_cooccurrence_graph([])
    assert out["nodes"] == []
    assert out["edges"] == []


def test_simple_pair():
    from engram.skill_cooccurrence_graph import build_cooccurrence_graph
    eps = [_Ep("e1", ["a", "b"])]
    out = build_cooccurrence_graph(eps)
    ids = [n["id"] for n in out["nodes"]]
    assert "a" in ids
    assert "b" in ids
    assert len(out["edges"]) == 1


def test_edge_weight_count():
    from engram.skill_cooccurrence_graph import build_cooccurrence_graph
    eps = [
        _Ep("e1", ["a", "b"]),
        _Ep("e2", ["a", "b"]),
        _Ep("e3", ["a", "b"]),
    ]
    out = build_cooccurrence_graph(eps)
    edge = out["edges"][0]
    assert edge["weight"] == 3


def test_degree_per_node():
    from engram.skill_cooccurrence_graph import build_cooccurrence_graph
    eps = [
        _Ep("e1", ["a", "b"]),
        _Ep("e2", ["a", "c"]),
        _Ep("e3", ["a", "d"]),
    ]
    out = build_cooccurrence_graph(eps)
    by_id = {n["id"]: n for n in out["nodes"]}
    assert by_id["a"]["degree"] == 3
    assert by_id["b"]["degree"] == 1


def test_payload_shape():
    from engram.skill_cooccurrence_graph import build_cooccurrence_graph
    out = build_cooccurrence_graph([])
    for k in ("nodes", "edges", "n_episodes_scanned"):
        assert k in out


def test_singleton_skill_no_edge():
    from engram.skill_cooccurrence_graph import build_cooccurrence_graph
    eps = [_Ep("e1", ["only_one"])]
    out = build_cooccurrence_graph(eps)
    assert out["edges"] == []
