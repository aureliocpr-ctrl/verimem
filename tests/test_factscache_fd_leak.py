"""DIR B — FactsCache.refresh() must not leak the semantic.db handle.

Codex tribunal finding (3-LLM verified 2026-05-28): the daemon's
`with sqlite3.connect() as conn` committed but never closed the connection.
On Windows (strict file locking) a lingering read handle blocks unlink and
can interfere with WAL checkpoint. Patch: explicit `conn.close()` in finally.

This loads the daemon SOURCE (docs/hooks/engram_embedding_daemon.py) directly,
runs refresh() against a temp WAL db, then asserts the db file can be unlinked
(the Windows-canonical proof that no handle is held).

HONEST NOTE (A4): on CPython the refcount GC closes a lingering connection at
refresh() scope-exit, so this guard tends to pass even pre-patch; it is a
GREEN regression guard, not the canonical RED. The canonical RED proving the
claim is tests/test_embedding_daemon_connect_leak.py ('DID NOT RAISE').
"""
from __future__ import annotations

import gc
import importlib.util
import sqlite3
import sys
from pathlib import Path

import numpy as np
import pytest


def _load_daemon_module():
    src = (
        Path(__file__).resolve().parents[1]
        / "docs" / "hooks" / "engram_embedding_daemon.py"
    )
    spec = importlib.util.spec_from_file_location(
        "engram_embedding_daemon_src", src,
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _fake_encoder(texts):
    """Stand-in encoder: returns L2-ish vectors without loading a model."""
    return np.ones((len(texts), 4), dtype=np.float32)


def _make_wal_db(path: Path, n: int = 3) -> None:
    conn = sqlite3.connect(str(path))
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute(
            "CREATE TABLE facts(id TEXT, proposition TEXT, topic TEXT, "
            "created_at REAL)"
        )
        for i in range(n):
            conn.execute(
                "INSERT INTO facts VALUES(?,?,?,?)",
                (f"f{i}", f"prop {i}", "test/slo", 0.0),
            )
        conn.commit()
    finally:
        conn.close()


class TestFactsCacheFdLeak:
    def test_refresh_does_not_hold_db_handle(self, tmp_path: Path):
        daemon = _load_daemon_module()
        db = tmp_path / "semantic.db"
        _make_wal_db(db, n=3)

        cache = daemon.FactsCache(_fake_encoder, db)
        stats = cache.refresh()
        assert stats["n_total"] == 3, stats

        # On Windows an open connection from refresh() blocks unlink with
        # PermissionError. Post-patch (explicit close) it must succeed.
        gc.collect()  # be fair to CPython refcount behavior
        db.unlink()
        assert not db.exists()

    def test_refresh_repeated_then_unlink(self, tmp_path: Path):
        daemon = _load_daemon_module()
        db = tmp_path / "semantic.db"
        _make_wal_db(db, n=2)
        cache = daemon.FactsCache(_fake_encoder, db)
        for _ in range(5):
            cache.refresh()
        gc.collect()
        # Clean up WAL sidecars if present, then the main db must unlink.
        for sidecar in (db.with_suffix(".db-wal"), db.with_suffix(".db-shm")):
            if sidecar.exists():
                sidecar.unlink()
        db.unlink()
        assert not db.exists()
