"""Cycle 198 (2026-05-23) — betweenness cache tests.

RED marker: ``from engram.betweenness_cache import
ensure_highway_cache`` must fail on master.
"""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

import pytest

# RED MARKER
from engram.betweenness_cache import ensure_highway_cache

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
CREATE TABLE IF NOT EXISTS causal_edges (
    src TEXT,
    dst TEXT,
    weight REAL DEFAULT 1.0
);
"""


@pytest.fixture
def small_graph_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "semantic.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript(_SCHEMA)
    rows = [
        (n, "p", "t", None, None, "model_claim", 1.0)
        for n in ("a1", "a2", "a3", "bridge", "b1", "b2", "b3")
    ]
    conn.executemany(
        "INSERT INTO facts (id, proposition, topic, lineage_to, "
        "superseded_by, status, created_at) VALUES (?,?,?,?,?,?,?)",
        rows,
    )
    for src, dst in [
        ("a1", "a2"), ("a2", "a3"), ("a1", "a3"),
        ("a3", "bridge"), ("bridge", "b3"),
        ("b1", "b2"), ("b2", "b3"), ("b1", "b3"),
    ]:
        conn.execute(
            "INSERT INTO causal_edges (src, dst, weight) VALUES (?,?,1.0)",
            (src, dst),
        )
    conn.commit()
    conn.close()
    return db_path


class TestEnsureHighwayCache:
    def test_missing_db_returns_empty(self, tmp_path: Path) -> None:
        out = ensure_highway_cache(tmp_path / "nope.db")
        assert out == []

    def test_first_call_computes_and_writes_cache(
        self, small_graph_db: Path, tmp_path: Path,
    ) -> None:
        cache_dir = tmp_path / "cache_dir"
        out = ensure_highway_cache(
            small_graph_db, cache_dir=cache_dir, k=5,
        )
        assert len(out) > 0
        cache_file = cache_dir / "betweenness_cache.json"
        assert cache_file.exists()

    def test_second_call_within_max_age_reads_cache(
        self, small_graph_db: Path, tmp_path: Path,
    ) -> None:
        cache_dir = tmp_path / "cache_dir"
        ensure_highway_cache(small_graph_db, cache_dir=cache_dir, k=5)
        # Modify cache file to detect "did we recompute?".
        cache_file = cache_dir / "betweenness_cache.json"
        payload = json.loads(cache_file.read_text(encoding="utf-8"))
        payload["highways"] = [["SENTINEL", 999.0]]
        cache_file.write_text(json.dumps(payload), encoding="utf-8")
        # Second call: same graph, fresh cache → MUST read sentinel.
        out = ensure_highway_cache(
            small_graph_db, cache_dir=cache_dir, k=5,
            max_age_seconds=3600,
        )
        assert out == [("SENTINEL", 999.0)]

    def test_force_refresh_bypasses_cache(
        self, small_graph_db: Path, tmp_path: Path,
    ) -> None:
        cache_dir = tmp_path / "cache_dir"
        ensure_highway_cache(small_graph_db, cache_dir=cache_dir, k=5)
        # Poison cache; force_refresh must ignore it.
        cache_file = cache_dir / "betweenness_cache.json"
        payload = json.loads(cache_file.read_text(encoding="utf-8"))
        payload["highways"] = [["POISON", 999.0]]
        cache_file.write_text(json.dumps(payload), encoding="utf-8")
        out = ensure_highway_cache(
            small_graph_db, cache_dir=cache_dir, k=5,
            force_refresh=True,
        )
        ids = {fid for fid, _ in out}
        assert "POISON" not in ids
        # Real recompute → "bridge" should rank high
        assert "bridge" in ids

    def test_stale_cache_recomputes(
        self, small_graph_db: Path, tmp_path: Path,
    ) -> None:
        cache_dir = tmp_path / "cache_dir"
        ensure_highway_cache(small_graph_db, cache_dir=cache_dir, k=5)
        cache_file = cache_dir / "betweenness_cache.json"
        payload = json.loads(cache_file.read_text(encoding="utf-8"))
        # Backdate cache by 1h.
        payload["computed_at"] = time.time() - 3600
        payload["highways"] = [["STALE", 1.0]]
        cache_file.write_text(json.dumps(payload), encoding="utf-8")
        out = ensure_highway_cache(
            small_graph_db, cache_dir=cache_dir, k=5,
            max_age_seconds=60,  # 1 min
        )
        ids = {fid for fid, _ in out}
        assert "STALE" not in ids

    def test_graph_change_invalidates_cache(
        self, small_graph_db: Path, tmp_path: Path,
    ) -> None:
        cache_dir = tmp_path / "cache_dir"
        ensure_highway_cache(small_graph_db, cache_dir=cache_dir, k=5)
        # Modify graph: add a new fact.
        conn = sqlite3.connect(str(small_graph_db))
        conn.execute(
            "INSERT INTO facts (id, proposition, topic, created_at) "
            "VALUES ('new-node', 'p', 't', 100.0)",
        )
        conn.commit()
        conn.close()
        # Cache should be invalidated (sig changed) → recompute.
        out = ensure_highway_cache(
            small_graph_db, cache_dir=cache_dir, k=20,
            max_age_seconds=3600,
        )
        assert len(out) > 0  # actually recomputed

    def test_cache_writes_required_fields(
        self, small_graph_db: Path, tmp_path: Path,
    ) -> None:
        cache_dir = tmp_path / "cache_dir"
        ensure_highway_cache(small_graph_db, cache_dir=cache_dir, k=5)
        payload = json.loads(
            (cache_dir / "betweenness_cache.json").read_text(
                encoding="utf-8",
            )
        )
        for key in ("semantic_db_path", "computed_at",
                     "graph_signature", "highways"):
            assert key in payload
