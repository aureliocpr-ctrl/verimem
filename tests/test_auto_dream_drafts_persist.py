"""Cycle 223 (2026-05-23) — Auto-Dream worker persists emergence drafts.

When ``_propose_via_engram`` builds the emergence_seed (cycle 219),
it should ALSO write the underlying drafts to disk for audit (cycle
222 ``persist_drafts``). The drafts land under::

    <engram_dir>/skill_drafts/<YYYYMMDD-HHMMSS>/

RED marker: ``_persist_emergence_drafts`` (or equivalent helper) does
not exist on master. We verify behaviour via a smoke test that drives
the path-detection + persistence wiring with a synthetic engram dir.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import numpy as np

from tests.causal_fixture_helper import add_causal_clique_edges
from verimem.auto_dream_worker import _persist_emergence_drafts


def _cluster_emb(seed: int, noise: float, sample: int) -> bytes:
    rng = np.random.default_rng(seed)
    c = rng.standard_normal(384).astype(np.float32)
    c /= np.linalg.norm(c) + 1e-9
    rng_n = np.random.default_rng(sample)
    n = rng_n.standard_normal(384).astype(np.float32) * noise
    out = c + n
    out /= np.linalg.norm(out) + 1e-9
    return out.tobytes()

_SCHEMA = """
CREATE TABLE IF NOT EXISTS facts (
    id TEXT PRIMARY KEY, proposition TEXT, topic TEXT, embedding BLOB,
    lineage_to TEXT, superseded_by TEXT,
    status TEXT DEFAULT 'model_claim', created_at REAL DEFAULT 0.0
);
"""


def _populate(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.executescript(_SCHEMA)
    rows = []
    edges = []
    for i in range(4):
        rows.append((
            f"a{i}", f"python fact {i} list dict iteration test",
            "lang/python",
            _cluster_emb(1, 0.05, 100 + i), None, None, "model_claim",
            float(i),
        ))
        for j in range(4):
            if i != j:
                edges.append((f"a{i}", f"a{j}"))
    conn.executemany(
        "INSERT INTO facts (id, proposition, topic, embedding, "
        "lineage_to, superseded_by, status, created_at) "
        "VALUES (?,?,?,?,?,?,?,?)", rows,
    )
    conn.commit()
    conn.close()
    add_causal_clique_edges(db_path, edges)


class TestPersistEmergenceDrafts:
    def test_writes_drafts_to_engram_skill_drafts_dir(
        self, tmp_path: Path,
    ) -> None:
        """When the corpus surfaces ≥1 emergent skill, the helper must
        write Markdown + meta files under <engram_dir>/skill_drafts/.
        """
        engram_dir = tmp_path / "engram"
        _populate(engram_dir / "semantic" / "semantic.db")
        result = _persist_emergence_drafts(
            engram_dir=engram_dir, max_n=3,
            min_community_size=3, min_topic_purity=0.5,
            min_cohesion=0.1,
        )
        assert result["n_written"] >= 1
        drafts_root = engram_dir / "skill_drafts"
        assert drafts_root.exists()
        batches = list(drafts_root.iterdir())
        assert len(batches) == 1
        md_files = list(batches[0].glob("*.md"))
        meta_files = list(batches[0].glob("*.meta.json"))
        assert len(md_files) >= 1
        assert len(meta_files) >= 1

    def test_empty_corpus_writes_nothing(self, tmp_path: Path) -> None:
        """No candidates → no batch directory created."""
        engram_dir = tmp_path / "engram"
        engram_dir.mkdir()
        # Empty semantic.db (schema only).
        sub = engram_dir / "semantic"
        sub.mkdir()
        conn = sqlite3.connect(str(sub / "semantic.db"))
        conn.executescript(_SCHEMA)
        conn.commit()
        conn.close()
        result = _persist_emergence_drafts(engram_dir=engram_dir, max_n=3)
        assert result["n_written"] == 0
        drafts_root = engram_dir / "skill_drafts"
        # Either the dir wasn't created OR it exists empty.
        if drafts_root.exists():
            assert not list(drafts_root.iterdir())

    def test_missing_db_returns_zero(self, tmp_path: Path) -> None:
        """No semantic.db at all → no crash, no drafts."""
        engram_dir = tmp_path / "engram"
        engram_dir.mkdir()
        result = _persist_emergence_drafts(engram_dir=engram_dir, max_n=3)
        assert result["n_written"] == 0
