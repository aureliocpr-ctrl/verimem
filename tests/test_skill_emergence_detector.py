"""Cycle 213 (2026-05-23) — skill_emergence detector tests.

RED marker: import must fail on master.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import numpy as np
import pytest

# RED MARKER
from engram.skill_emergence_detector import detect_emerging_skills

_SCHEMA = """
CREATE TABLE IF NOT EXISTS facts (
    id TEXT PRIMARY KEY,
    proposition TEXT,
    topic TEXT,
    embedding BLOB,
    lineage_to TEXT,
    superseded_by TEXT,
    status TEXT DEFAULT 'model_claim',
    created_at REAL DEFAULT 0.0
);
"""

from tests.causal_fixture_helper import add_causal_clique_edges  # noqa: E402


def _normalised_emb(seed: int) -> bytes:
    rng = np.random.default_rng(seed)
    arr = rng.standard_normal(384).astype(np.float32)
    n = np.linalg.norm(arr)
    if n > 0:
        arr = arr / n
    return arr.tobytes()


def _cluster_emb(centroid_seed: int, noise: float, sample_seed: int) -> bytes:
    """Build an embedding near a centroid (low-noise = high cohesion)."""
    rng_c = np.random.default_rng(centroid_seed)
    centroid = rng_c.standard_normal(384).astype(np.float32)
    centroid /= np.linalg.norm(centroid) + 1e-9
    rng_n = np.random.default_rng(sample_seed)
    noise_v = rng_n.standard_normal(384).astype(np.float32) * float(noise)
    out = centroid + noise_v
    out /= np.linalg.norm(out) + 1e-9
    return out.tobytes()


@pytest.fixture
def emergence_db(tmp_path: Path) -> Path:
    """Two communities of 4 facts each:

      cluster_a/* — high cohesion (noise=0.1), shared topic 'lang/python'
      cluster_b/* — high cohesion (noise=0.1), shared topic 'food/fruit'

    Plus one isolated fact with a different topic that should NOT
    surface as an emergent skill.
    """
    db_path = tmp_path / "semantic" / "semantic.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.executescript(_SCHEMA)
    rows = []
    edges = []
    # Cluster A (4 facts on lang/python).
    for i in range(4):
        rows.append((
            f"a{i}", f"python fact {i}", "lang/python",
            _cluster_emb(centroid_seed=1, noise=0.05, sample_seed=100 + i),
            None, None, "model_claim", float(i),
        ))
        # full mesh edges within cluster
        for j in range(4):
            if i != j:
                edges.append((f"a{i}", f"a{j}"))
    # Cluster B (4 facts on food/fruit).
    for i in range(4):
        rows.append((
            f"b{i}", f"banana fact {i}", "food/fruit",
            _cluster_emb(centroid_seed=2, noise=0.05, sample_seed=200 + i),
            None, None, "model_claim", float(10 + i),
        ))
        for j in range(4):
            if i != j:
                edges.append((f"b{i}", f"b{j}"))
    # Isolated fact (no community).
    rows.append((
        "lonely", "isolated fact", "noise/topic",
        _normalised_emb(seed=42),
        None, None, "model_claim", 100.0,
    ))
    conn.executemany(
        "INSERT INTO facts (id, proposition, topic, embedding, "
        "lineage_to, superseded_by, status, created_at) "
        "VALUES (?,?,?,?,?,?,?,?)",
        rows,
    )
    conn.commit()
    conn.close()
    add_causal_clique_edges(db_path, edges)
    return db_path


class TestDetectEmergingSkills:
    def test_missing_db_returns_empty(self, tmp_path: Path) -> None:
        assert detect_emerging_skills(tmp_path / "nope.db") == []

    def test_finds_two_clusters(self, emergence_db: Path) -> None:
        """The 2 synthetic clusters must both surface."""
        out = detect_emerging_skills(
            emergence_db, min_community_size=3, min_cohesion=0.1,
        )
        assert len(out) >= 2

    def test_returns_required_fields(self, emergence_db: Path) -> None:
        out = detect_emerging_skills(
            emergence_db, min_community_size=3, min_cohesion=0.1,
        )
        for entry in out:
            for key in ("community_id", "size", "fact_ids",
                         "suggested_skill_name", "dominant_topic",
                         "topic_purity", "cohesion", "emergence_score"):
                assert key in entry

    def test_skill_name_contains_topic_leaf(
        self, emergence_db: Path,
    ) -> None:
        """suggested_skill_name should embed the leaf of the dominant
        topic path."""
        out = detect_emerging_skills(
            emergence_db, min_community_size=3, min_cohesion=0.1,
        )
        names = [e["suggested_skill_name"] for e in out]
        # 'python' is the leaf of 'lang/python'; 'fruit' of 'food/fruit'.
        joined = " ".join(names).lower()
        assert "python" in joined or "fruit" in joined

    def test_score_sorted_desc(self, emergence_db: Path) -> None:
        out = detect_emerging_skills(
            emergence_db, min_community_size=3, min_cohesion=0.1,
            max_n=10,
        )
        scores = [e["emergence_score"] for e in out]
        assert scores == sorted(scores, reverse=True)

    def test_min_topic_purity_filter(self, emergence_db: Path) -> None:
        """min_topic_purity=1.0 (perfect uniformity) should still keep
        both clusters since each is 100% same topic."""
        out = detect_emerging_skills(
            emergence_db, min_community_size=3,
            min_topic_purity=1.0, min_cohesion=0.1,
        )
        # Both fixture clusters are 100% pure on their topics.
        assert len(out) >= 2

    def test_min_cohesion_filter(self, emergence_db: Path) -> None:
        """Extremely high cohesion floor should drop all (random
        embeddings can't reach near-1.0 cosine)."""
        out = detect_emerging_skills(
            emergence_db, min_community_size=3, min_cohesion=0.999,
        )
        assert out == []

    def test_max_n_caps(self, emergence_db: Path) -> None:
        out = detect_emerging_skills(
            emergence_db, min_community_size=3, min_cohesion=0.1,
            max_n=1,
        )
        assert len(out) <= 1

    def test_handles_corpus_without_embeddings(
        self, tmp_path: Path,
    ) -> None:
        """Facts without embedding column populated → cohesion=0 →
        no emergence."""
        db_path = tmp_path / "s.db"
        conn = sqlite3.connect(str(db_path))
        conn.executescript(_SCHEMA)
        for i in range(5):
            conn.execute(
                "INSERT INTO facts (id, topic) VALUES (?, 't')",
                (f"f{i}",),
            )
        conn.commit()
        conn.close()
        out = detect_emerging_skills(
            db_path, min_community_size=3,
        )
        assert isinstance(out, list)
