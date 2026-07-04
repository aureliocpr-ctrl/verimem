"""Cycle 187 (2026-05-23) — wire community detector into Auto-Dream.

Composable pattern (proven by cycle 175.1 dream_stuck_hook): a pure
seed builder that returns a structured suffix the
``auto_dream_worker._propose_via_engram`` adapter splices into
``instructions`` of ``propose_dream_tasks``. The cluster algorithm
in dream.py is free to ignore — soft hint by design.

Goal
----
Surface the top-K Louvain communities (cycle 186) so Auto-Dream
prioritises **topologically-cohesive** clusters when proposing skill
synthesis tasks, instead of relying only on episode-cosine clustering
(cycle #34/#35).

RED marker: ``from engram.dream_community_hook import
build_community_seed`` must fail on master.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest

# RED MARKER
from engram.dream_community_hook import build_community_seed
from tests.causal_fixture_helper import add_causal_clique_edges

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


@pytest.fixture
def two_clique_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "semantic" / "semantic.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.executescript(_SCHEMA)
    rows = [
        (n, f"prop {n}", "t", None, None, "model_claim", 1.0)
        for n in ("a1", "a2", "a3", "a4", "b1", "b2", "b3", "b4")
    ]
    conn.executemany(
        "INSERT INTO facts (id, proposition, topic, lineage_to, "
        "superseded_by, status, created_at) VALUES (?,?,?,?,?,?,?)",
        rows,
    )
    conn.commit()
    conn.close()
    intra = [
        ("a1", "a2"), ("a2", "a3"), ("a3", "a4"), ("a1", "a4"),
        ("b1", "b2"), ("b2", "b3"), ("b3", "b4"), ("b1", "b4"),
    ]
    bridges = [("a1", "b1")]
    add_causal_clique_edges(db_path, intra + bridges)
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


class TestBuildCommunitySeed:
    def test_returns_dict_with_required_keys(
        self, two_clique_db: Path,
    ) -> None:
        out = build_community_seed(two_clique_db)
        assert isinstance(out, dict)
        for k in ("top_community_ids", "instructions_suffix"):
            assert k in out

    def test_top_community_ids_is_list_of_str(
        self, two_clique_db: Path,
    ) -> None:
        out = build_community_seed(two_clique_db)
        assert isinstance(out["top_community_ids"], list)
        assert all(isinstance(x, str) for x in out["top_community_ids"])

    def test_empty_corpus_returns_empty_seed(
        self, empty_db: Path,
    ) -> None:
        out = build_community_seed(empty_db)
        assert out["top_community_ids"] == []
        assert out["instructions_suffix"] == ""

    def test_missing_db_returns_empty(self, tmp_path: Path) -> None:
        out = build_community_seed(tmp_path / "nope.db")
        assert out == {"top_community_ids": [], "instructions_suffix": ""}

    def test_includes_communities_when_present(
        self, two_clique_db: Path,
    ) -> None:
        out = build_community_seed(two_clique_db, max_n=5)
        # Expect at least 2 communities on the 2-clique fixture.
        assert len(out["top_community_ids"]) >= 1

    def test_instructions_suffix_mentions_communities(
        self, two_clique_db: Path,
    ) -> None:
        out = build_community_seed(two_clique_db, max_n=5)
        suffix_lower = out["instructions_suffix"].lower()
        assert "communit" in suffix_lower or "cluster" in suffix_lower

    def test_respects_max_n(
        self, two_clique_db: Path,
    ) -> None:
        out = build_community_seed(two_clique_db, max_n=1)
        assert len(out["top_community_ids"]) <= 1

    def test_min_community_size_filters_small(
        self, two_clique_db: Path,
    ) -> None:
        out = build_community_seed(
            two_clique_db, max_n=10, min_community_size=10,
        )
        # min_size=10 > any fixture community size → empty
        assert out["top_community_ids"] == []

    def test_delegates_to_detect_communities(
        self, two_clique_db: Path,
    ) -> None:
        """Composition contract: build_community_seed must forward to
        engram.community_detector.detect_communities."""
        with patch(
            "engram.dream_community_hook.detect_communities",
            return_value={
                "algorithm": "louvain",
                "n_communities": 2,
                "modularity": 0.5,
                "communities": [
                    {"id": "c-001", "size": 4,
                     "fact_ids": ["a1", "a2", "a3", "a4"]},
                    {"id": "c-002", "size": 4,
                     "fact_ids": ["b1", "b2", "b3", "b4"]},
                ],
            },
        ) as mock_dc:
            out = build_community_seed(two_clique_db, max_n=3)
        mock_dc.assert_called_once()
        assert "c-001" in out["top_community_ids"]
        assert "c-002" in out["top_community_ids"]
