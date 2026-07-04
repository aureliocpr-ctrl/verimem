"""Cycle 219 (2026-05-23) — dream_emergence_hook tests.

RED marker: ``from engram.dream_emergence_hook import build_emergence_seed``
must fail on master.

Composable pattern proven by cycle 175.1 (stuck), cycle 187 (community),
cycle 211 (thompson). Cycle 219 builds the FOURTH hook over the
cycle 213 + 217 emergent skill draft pipeline.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import numpy as np
import pytest

# RED MARKER
from engram.dream_emergence_hook import build_emergence_seed
from tests.causal_fixture_helper import add_causal_clique_edges


def _cluster_emb(centroid_seed: int, noise: float, sample_seed: int) -> bytes:
    rng_c = np.random.default_rng(centroid_seed)
    centroid = rng_c.standard_normal(384).astype(np.float32)
    centroid /= np.linalg.norm(centroid) + 1e-9
    rng_n = np.random.default_rng(sample_seed)
    noise_v = rng_n.standard_normal(384).astype(np.float32) * float(noise)
    out = centroid + noise_v
    out /= np.linalg.norm(out) + 1e-9
    return out.tobytes()

_SCHEMA = """
CREATE TABLE IF NOT EXISTS facts (
    id TEXT PRIMARY KEY, proposition TEXT, topic TEXT, embedding BLOB,
    lineage_to TEXT, superseded_by TEXT,
    status TEXT DEFAULT 'model_claim', created_at REAL DEFAULT 0.0
);
"""


@pytest.fixture
def emergence_db(tmp_path: Path) -> Path:
    db = tmp_path / "semantic" / "semantic.db"
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db))
    conn.executescript(_SCHEMA)
    rows = []
    edges = []
    for i in range(4):
        rows.append((
            f"a{i}", f"python fact {i} list dict iteration",
            "lang/python",
            _cluster_emb(1, 0.05, 100 + i), None, None, "model_claim",
            float(i),
        ))
        for j in range(4):
            if i != j:
                edges.append((f"a{i}", f"a{j}"))
    for i in range(4):
        rows.append((
            f"b{i}", f"banana fact {i} fruit yellow",
            "food/fruit",
            _cluster_emb(2, 0.05, 200 + i), None, None, "model_claim",
            float(10 + i),
        ))
        for j in range(4):
            if i != j:
                edges.append((f"b{i}", f"b{j}"))
    conn.executemany(
        "INSERT INTO facts (id, proposition, topic, embedding, "
        "lineage_to, superseded_by, status, created_at) "
        "VALUES (?,?,?,?,?,?,?,?)",
        rows,
    )
    conn.commit()
    conn.close()
    add_causal_clique_edges(db, edges)
    return db


class TestBuildEmergenceSeed:
    def test_missing_db_returns_empty(self, tmp_path: Path) -> None:
        seed = build_emergence_seed(tmp_path / "nope.db", max_n=3)
        assert seed["draft_skill_names"] == []
        assert seed["instructions_suffix"] == ""

    def test_finds_emergent_skills_on_real_clusters(
        self, emergence_db: Path,
    ) -> None:
        seed = build_emergence_seed(
            emergence_db, max_n=5, min_community_size=3,
            min_topic_purity=0.5, min_cohesion=0.1,
        )
        # 2-cluster fixture should produce >=1 emergent skill seed.
        assert len(seed["draft_skill_names"]) >= 1
        assert seed["instructions_suffix"]
        # Suffix must cite each emergent skill name AND the cycle
        # marker so downstream readers know the seed source.
        assert "219" in seed["instructions_suffix"]
        for name in seed["draft_skill_names"]:
            assert name in seed["instructions_suffix"]

    def test_max_n_caps(self, emergence_db: Path) -> None:
        seed = build_emergence_seed(
            emergence_db, max_n=1, min_community_size=3,
            min_topic_purity=0.5, min_cohesion=0.1,
        )
        assert len(seed["draft_skill_names"]) <= 1

    def test_seed_includes_evidence_in_suffix(
        self, emergence_db: Path,
    ) -> None:
        """Suffix should embed at least one piece of evidence (size or
        purity) so the dream cluster algorithm can reason about
        signal strength."""
        seed = build_emergence_seed(
            emergence_db, max_n=3, min_community_size=3,
            min_topic_purity=0.5, min_cohesion=0.1,
        )
        suf = seed["instructions_suffix"]
        # Must include either 'size' or 'purity' literal token —
        # demonstrating evidence is wired through.
        assert "size" in suf or "purity" in suf

    def test_threshold_filters_out_weak_communities(
        self, emergence_db: Path,
    ) -> None:
        """Very high cohesion floor → no candidates, empty seed."""
        seed = build_emergence_seed(
            emergence_db, max_n=5, min_community_size=3,
            min_topic_purity=0.5, min_cohesion=0.999,
        )
        assert seed["draft_skill_names"] == []
        assert seed["instructions_suffix"] == ""

    def test_handles_empty_corpus_gracefully(
        self, tmp_path: Path,
    ) -> None:
        db = tmp_path / "empty.db"
        conn = sqlite3.connect(str(db))
        conn.executescript(_SCHEMA)
        conn.commit()
        conn.close()
        seed = build_emergence_seed(db, max_n=3)
        assert seed["draft_skill_names"] == []
        assert seed["instructions_suffix"] == ""
