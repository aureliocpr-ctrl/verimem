"""Cycle 189 (2026-05-23) — get_highway_nodes detector (sampled betweenness).

Closes gap §6.1 of docs/sota/highway-nodes-pagerank-cache.md
(cycle 188). Pure function over networkx betweenness_centrality
identifying the top-K fact ids that bridge otherwise-disjoint
communities.

RED marker: ``from engram.highway_nodes import get_highway_nodes``
must fail on master.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

# RED MARKER
from engram.highway_nodes import get_highway_nodes
from tests.causal_fixture_helper import add_causal_clique_edges

_SCHEMA = """
CREATE TABLE IF NOT EXISTS facts (
    id TEXT PRIMARY KEY,
    proposition TEXT,
    topic TEXT,
    lineage_to TEXT,
    superseded_by TEXT,
    status TEXT DEFAULT 'model_claim',
    created_at REAL
);
"""


@pytest.fixture
def bowtie_db(tmp_path: Path) -> Path:
    """Bowtie fixture: two K3 cliques bridged by a single 'bridge' node.

        A1 - A2          B1 - B2
         \\ /             \\ /
          A3 -- BRIDGE -- B3

    The BRIDGE node must have the highest betweenness centrality.
    """
    db_path = tmp_path / "semantic" / "semantic.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.executescript(_SCHEMA)
    nodes = ["a1", "a2", "a3", "bridge", "b1", "b2", "b3"]
    rows = [
        (n, f"prop {n}", "t", None, None, "model_claim", 1.0) for n in nodes
    ]
    conn.executemany(
        "INSERT INTO facts (id, proposition, topic, lineage_to, "
        "superseded_by, status, created_at) VALUES (?,?,?,?,?,?,?)",
        rows,
    )
    conn.commit()
    conn.close()
    edges = [
        ("a1", "a2"), ("a2", "a3"), ("a1", "a3"),    # clique A
        ("a3", "bridge"), ("bridge", "b3"),           # bridge
        ("b1", "b2"), ("b2", "b3"), ("b1", "b3"),    # clique B
    ]
    add_causal_clique_edges(db_path, edges)
    return db_path


@pytest.fixture
def empty_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "semantic" / "semantic.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.executescript(_SCHEMA)
    conn.commit()
    conn.close()
    return db_path


class TestGetHighwayNodes:
    def test_returns_list_of_tuples(self, bowtie_db: Path) -> None:
        out = get_highway_nodes(bowtie_db)
        assert isinstance(out, list)
        for entry in out:
            assert isinstance(entry, tuple) and len(entry) == 2
            assert isinstance(entry[0], str)
            assert isinstance(entry[1], float)

    def test_bowtie_bridge_has_highest_betweenness(
        self, bowtie_db: Path,
    ) -> None:
        """Bowtie graph: the 'bridge' node sits on every path between
        clique A and clique B → must dominate betweenness ranking."""
        out = get_highway_nodes(bowtie_db, k=5)
        assert len(out) > 0
        top_id, top_score = out[0]
        assert top_id == "bridge", (
            f"expected 'bridge' as #1 highway, got {top_id!r} "
            f"(full ranking: {out})"
        )
        assert top_score > 0.0

    def test_empty_db_returns_empty(self, empty_db: Path) -> None:
        out = get_highway_nodes(empty_db)
        assert out == []

    def test_missing_db_defensive(self, tmp_path: Path) -> None:
        out = get_highway_nodes(tmp_path / "nope.db")
        assert out == []

    def test_respects_k_cap(self, bowtie_db: Path) -> None:
        out = get_highway_nodes(bowtie_db, k=2)
        assert len(out) <= 2

    def test_scores_sorted_descending(self, bowtie_db: Path) -> None:
        """Result must be ordered by score DESC (highway #1 first)."""
        out = get_highway_nodes(bowtie_db, k=10)
        scores = [s for _, s in out]
        assert scores == sorted(scores, reverse=True), (
            f"scores not sorted desc: {scores}"
        )

    def test_excludes_superseded_facts(self, tmp_path: Path) -> None:
        db_path = tmp_path / "semantic" / "s.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_path))
        conn.executescript(_SCHEMA)
        conn.executemany(
            "INSERT INTO facts (id, proposition, topic, lineage_to, "
            "superseded_by, status, created_at) VALUES (?,?,?,?,?,?,?)",
            [
                ("alive-1", "p", "t", None, None, "model_claim", 1.0),
                ("alive-2", "p", "t", None, None, "model_claim", 1.0),
                ("alive-3", "p", "t", None, None, "model_claim", 1.0),
                ("dead-1", "p", "t", None, "alive-1", "model_claim", 1.0),
            ],
        )
        conn.commit()
        conn.close()
        add_causal_clique_edges(
            db_path, [("alive-1", "alive-2"), ("alive-2", "alive-3")],
        )
        out = get_highway_nodes(db_path, k=10)
        ids = {x[0] for x in out}
        assert "dead-1" not in ids

    def test_handles_isolated_nodes(self, tmp_path: Path) -> None:
        """Nodes without any edge have betweenness 0 and are still
        ranked (allowed) but not produce a crash."""
        db_path = tmp_path / "iso.db"
        conn = sqlite3.connect(str(db_path))
        conn.executescript(_SCHEMA)
        conn.executemany(
            "INSERT INTO facts (id, proposition, topic, lineage_to, "
            "superseded_by, status, created_at) VALUES (?,?,?,?,?,?,?)",
            [
                ("iso-1", "p", "t", None, None, "model_claim", 1.0),
                ("iso-2", "p", "t", None, None, "model_claim", 1.0),
            ],
        )
        conn.commit()
        conn.close()
        # No edges → no exception, possibly empty / all zero
        out = get_highway_nodes(db_path, k=5)
        assert isinstance(out, list)
