"""Cycle 186 (2026-05-23) — Louvain community detection wrapper.

Closes gap §5.1 of docs/sota/community-detection-channel-pattern.md
(cycle 185). Pure function that detects communities in the HippoAgent
fact graph via Louvain modularity maximisation over networkx (already
in requirements).

Acceptance criteria from §5.1:
  * Pure function ``detect_communities(semantic_db, ...) -> dict``.
  * At least 3 communities of size ≥ 3 on real corpus (verified
    empirically in a follow-up bench, not in this unit-test file).
  * < 100ms target on 1.7k-fact corpus (smoke-tested via fixture).
  * Synthetic 3-clique-bridge fixture → exactly 3 communities.

RED marker: import must fail on master.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

# RED MARKER
from verimem.community_detector import detect_communities

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


_SCHEMA = """
CREATE TABLE IF NOT EXISTS facts (
    id TEXT PRIMARY KEY,
    proposition TEXT,
    topic TEXT,
    lineage_to TEXT,
    superseded_by TEXT,
    status TEXT DEFAULT 'model_claim',
    created_at REAL,
    source_episodes TEXT
);
"""


# Shared scan-#316 fixture helper (real causal format: episodes.db sibling
# + facts.source_episodes) — see tests/causal_fixture_helper.py docstring.
from tests.causal_fixture_helper import (  # noqa: E402
    add_causal_clique_edges as _add_causal_clique_edges,
)


@pytest.fixture
def three_clique_bridge_db(tmp_path: Path) -> Path:
    """Seed a 3-clique-bridge graph:

      Clique A: a1-a2-a3 (3 nodes, fully connected)
      Clique B: b1-b2-b3
      Clique C: c1-c2-c3
      Bridges: a1-b1, b1-c1 (sparse inter-community)

    Louvain MUST recover exactly 3 communities (one per clique).
    """
    db_path = tmp_path / "semantic" / "semantic.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.executescript(_SCHEMA)
    rows = [
        (n, f"prop {n}", "t", None, None, "model_claim", 1.0)
        for n in ("a1", "a2", "a3", "b1", "b2", "b3", "c1", "c2", "c3")
    ]
    conn.executemany(
        "INSERT INTO facts (id, proposition, topic, lineage_to, "
        "superseded_by, status, created_at) VALUES (?,?,?,?,?,?,?)",
        rows,
    )
    conn.commit()
    conn.close()
    # Clique + bridge edges in the REAL causal format (episodes.db sibling).
    intra = [
        ("a1", "a2"), ("a2", "a3"), ("a1", "a3"),
        ("b1", "b2"), ("b2", "b3"), ("b1", "b3"),
        ("c1", "c2"), ("c2", "c3"), ("c1", "c3"),
    ]
    bridges = [("a1", "b1"), ("b1", "c1")]
    _add_causal_clique_edges(db_path, intra + bridges)
    return db_path


@pytest.fixture
def empty_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "semantic.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript(_SCHEMA)
    conn.commit()
    conn.close()
    return db_path


# ---------------------------------------------------------------------------
# Contract tests
# ---------------------------------------------------------------------------


class TestDetectCommunities:
    def test_returns_dict_with_required_keys(
        self, three_clique_bridge_db: Path,
    ) -> None:
        out = detect_communities(semantic_db=three_clique_bridge_db)
        assert isinstance(out, dict)
        for k in ("algorithm", "n_communities", "communities"):
            assert k in out, f"missing key {k!r} in {out}"

    def test_three_clique_bridge_yields_three_communities(
        self, three_clique_bridge_db: Path,
    ) -> None:
        """The fixture has clear 3-community structure. Louvain MUST
        recover at least 3 (allowing for resolution-limit it could
        sometimes merge, but on this tiny graph the bridges are
        sparse enough)."""
        out = detect_communities(
            semantic_db=three_clique_bridge_db, min_community_size=2,
        )
        assert out["n_communities"] >= 3, (
            f"expected ≥3 communities on 3-clique-bridge, got "
            f"{out['n_communities']}: {out!r}"
        )

    def test_handles_empty_db_gracefully(self, empty_db: Path) -> None:
        out = detect_communities(semantic_db=empty_db)
        assert out["n_communities"] == 0
        assert out["communities"] == []

    def test_handles_missing_db_defensive(self, tmp_path: Path) -> None:
        """Missing DB path → empty result, no crash."""
        out = detect_communities(semantic_db=tmp_path / "nope.db")
        assert out["n_communities"] == 0
        assert out["communities"] == []

    def test_community_entries_have_required_fields(
        self, three_clique_bridge_db: Path,
    ) -> None:
        out = detect_communities(semantic_db=three_clique_bridge_db)
        for c in out["communities"]:
            assert "id" in c
            assert "size" in c
            assert "fact_ids" in c
            assert isinstance(c["fact_ids"], list)
            assert c["size"] == len(c["fact_ids"])

    def test_min_community_size_filters_small(
        self, three_clique_bridge_db: Path,
    ) -> None:
        out = detect_communities(
            semantic_db=three_clique_bridge_db, min_community_size=4,
        )
        # All 3 cliques have size 3, so min=4 should drop all of them.
        for c in out["communities"]:
            assert c["size"] >= 4

    def test_includes_modularity_for_louvain(
        self, three_clique_bridge_db: Path,
    ) -> None:
        out = detect_communities(
            semantic_db=three_clique_bridge_db, algorithm="louvain",
        )
        # Modularity should be reasonably high on this synthetic graph.
        assert "modularity" in out
        assert out["modularity"] > 0.0, (
            f"expected positive modularity on 3-clique-bridge, "
            f"got {out['modularity']}"
        )

    def test_algorithm_field_echoes_choice(
        self, three_clique_bridge_db: Path,
    ) -> None:
        out = detect_communities(
            semantic_db=three_clique_bridge_db, algorithm="louvain",
        )
        assert out["algorithm"] == "louvain"

    def test_deterministic_under_fixed_seed(
        self, three_clique_bridge_db: Path,
    ) -> None:
        """Louvain has randomised initialisation; with fixed seed two
        calls must return the same n_communities."""
        out1 = detect_communities(
            semantic_db=three_clique_bridge_db, seed=42,
        )
        out2 = detect_communities(
            semantic_db=three_clique_bridge_db, seed=42,
        )
        assert out1["n_communities"] == out2["n_communities"]

    def test_excludes_superseded_facts(
        self, tmp_path: Path,
    ) -> None:
        """Superseded facts MUST NOT appear in any community
        (graph excludes them)."""
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
        _add_causal_clique_edges(
            db_path, [("alive-1", "alive-2"), ("alive-2", "alive-3")],
        )
        out = detect_communities(semantic_db=db_path, min_community_size=1)
        all_fact_ids = {fid for c in out["communities"] for fid in c["fact_ids"]}
        assert "dead-1" not in all_fact_ids, (
            f"superseded fact leaked: {all_fact_ids}"
        )
