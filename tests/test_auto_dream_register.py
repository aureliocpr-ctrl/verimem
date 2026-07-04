"""Cycle 230 (2026-05-23) — Auto-Dream worker registers emergence drafts as facts.

After cycle 223 persists drafts to disk, cycle 230 ALSO writes them
into the live ``semantic.db`` as soft ``emerging_skill/*`` facts.

This is observability-side-effect only — failure must NOT raise.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import numpy as np

from tests.causal_fixture_helper import add_causal_clique_edges

_SCHEMA = """
CREATE TABLE IF NOT EXISTS facts (
    id TEXT PRIMARY KEY,
    proposition TEXT,
    topic TEXT,
    confidence REAL DEFAULT 0.5,
    source_episodes TEXT DEFAULT '[]',
    created_at REAL DEFAULT 0.0,
    embedding BLOB,
    superseded_by TEXT,
    superseded_at REAL,
    superseded_reason TEXT,
    verified_by TEXT DEFAULT '[]',
    status TEXT DEFAULT 'model_claim',
    lineage_to TEXT,
    lineage_parents TEXT
);
"""


def _cluster_emb(seed: int, noise: float, sample: int) -> bytes:
    rng = np.random.default_rng(seed)
    c = rng.standard_normal(384).astype(np.float32)
    c /= np.linalg.norm(c) + 1e-9
    rng_n = np.random.default_rng(sample)
    n = rng_n.standard_normal(384).astype(np.float32) * noise
    out = c + n
    out /= np.linalg.norm(out) + 1e-9
    return out.tobytes()


def _populate(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.executescript(_SCHEMA)
    rows = []
    edges = []
    for i in range(4):
        rows.append((
            f"a{i}", f"python fact {i} list dict iteration", "lang/python",
            _cluster_emb(1, 0.05, 100 + i),
        ))
        for j in range(4):
            if i != j:
                edges.append((f"a{i}", f"a{j}"))
    conn.executemany(
        "INSERT INTO facts (id, proposition, topic, embedding, "
        "lineage_to, superseded_by, status, created_at, "
        "confidence, source_episodes, verified_by) "
        "VALUES (?,?,?,?,?,?,'model_claim',0.5,0.5,'[]','[]')",
        [(r[0], r[1], r[2], r[3], None, None) for r in rows],
    )
    conn.commit()
    conn.close()
    add_causal_clique_edges(db_path, edges)


class TestAutoDreamRegisterIntegration:
    def test_propose_via_engram_registers_facts(
        self, tmp_path: Path, monkeypatch,
    ) -> None:
        """When ``_propose_via_engram`` runs and the corpus surfaces
        candidates, those drafts must land as ``emerging_skill/*``
        facts in the live DB."""
        engram_dir = tmp_path / "engram"
        _populate(engram_dir / "semantic" / "semantic.db")
        # Empty skills + episodes (stub paths so worker doesn't crash
        # on missing tables).
        (engram_dir / "skills").mkdir(parents=True, exist_ok=True)
        # exist_ok: add_causal_clique_edges already created episodes/ for
        # the sibling episodes.db (real causal-edge location, scan #316).
        (engram_dir / "episodes").mkdir(parents=True, exist_ok=True)
        sk_db = engram_dir / "skills" / "skills_index.db"
        conn = sqlite3.connect(str(sk_db))
        conn.execute(
            "CREATE TABLE skills ("
            "id TEXT PRIMARY KEY, status TEXT, trials INTEGER, "
            "fitness REAL)",
        )
        conn.commit()
        conn.close()
        ep_db = engram_dir / "episodes" / "episodes.db"
        conn = sqlite3.connect(str(ep_db))
        conn.execute(
            "CREATE TABLE episodes (id TEXT PRIMARY KEY, "
            "task_text TEXT, outcome TEXT)",
        )
        conn.commit()
        conn.close()

        # Stub propose_dream_tasks to avoid downstream LLM dependency.
        import engram.auto_dream_worker as m
        import engram.dream as dream_mod

        def _fake_propose(*, live_dirs, shadow_root, **kw):
            shadow_root.mkdir(parents=True, exist_ok=True)
            return {
                "dream_id": "stub",
                "shadow_root": str(shadow_root),
                "pending_tasks": [], "instructions": kw.get("instructions", ""),
                "summary": "stub",
            }
        monkeypatch.setattr(dream_mod, "propose_dream_tasks", _fake_propose)

        # Run.
        m._propose_via_engram(engram_dir=engram_dir)

        # Verify: live semantic.db now has at least one
        # 'emerging_skill/*' fact.
        conn = sqlite3.connect(
            str(engram_dir / "semantic" / "semantic.db"),
        )
        rows = conn.execute(
            "SELECT id, topic FROM facts WHERE topic LIKE 'emerging_skill/%'",
        ).fetchall()
        conn.close()
        assert len(rows) >= 1, (
            "Auto-Dream firing should have registered ≥1 emerging skill"
        )
