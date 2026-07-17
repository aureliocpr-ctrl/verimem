"""Cycle 216 (2026-05-23) — RED: auto_dream_worker semantic_db resolution.

Bug A4: ``_live_dirs_from`` picks ``engram_dir/semantic.db`` when it
exists, even if it's empty. The real corpus lives at
``engram_dir/semantic/semantic.db``. Auto-Dream silently runs against
empty DB → 3-hook composition (stuck/community/thompson) gets nothing.

Empirical evidence (2026-05-23 02:20 EU/Rome):
  ~/.engram/semantic.db         → 36864 B, 0 facts
  ~/.engram/semantic/semantic.db → 7471104 B, 1707 facts

This test pins the fixed behaviour: when BOTH paths exist, prefer the
nested one (it's the canonical location since the engram package
restructure). When ONLY flat exists, fall back. When neither, return
the nested default (caller will get a graceful empty corpus).
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from verimem.auto_dream_worker import _live_dirs_from


def _touch_flat(engram_dir: Path) -> Path:
    """Create an empty ``semantic.db`` directly under engram_dir."""
    p = engram_dir / "semantic.db"
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(p))
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS facts ("
            "id TEXT PRIMARY KEY, proposition TEXT, embedding BLOB)"
        )
        conn.commit()
    finally:
        conn.close()
    return p


def _touch_nested(engram_dir: Path) -> Path:
    """Create the canonical ``semantic/semantic.db``."""
    p = engram_dir / "semantic" / "semantic.db"
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(p))
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS facts ("
            "id TEXT PRIMARY KEY, proposition TEXT, embedding BLOB)"
        )
        # Insert 5 fake facts so it's empirically non-empty.
        for i in range(5):
            conn.execute(
                "INSERT INTO facts (id, proposition, embedding) VALUES (?, ?, ?)",
                (f"f{i}", f"prop {i}", b"\x00" * 1536),
            )
        conn.commit()
    finally:
        conn.close()
    return p


class TestSemanticDbResolution:
    def test_prefers_nested_when_both_exist(self, tmp_path: Path) -> None:
        """When BOTH flat and nested exist, prefer nested (canonical)."""
        _touch_flat(tmp_path)
        _touch_nested(tmp_path)

        out = _live_dirs_from(tmp_path)
        assert out["semantic_db"] == tmp_path / "semantic" / "semantic.db"

    def test_falls_back_to_flat_when_nested_missing(
        self, tmp_path: Path,
    ) -> None:
        """When only flat exists (legacy), fall back to it."""
        _touch_flat(tmp_path)
        # Nested NOT created.

        out = _live_dirs_from(tmp_path)
        assert out["semantic_db"] == tmp_path / "semantic.db"

    def test_returns_nested_path_when_neither_exists(
        self, tmp_path: Path,
    ) -> None:
        """When neither exists, return nested as the future location."""
        out = _live_dirs_from(tmp_path)
        # propose_dream_tasks tolerates missing DBs → caller is OK.
        assert out["semantic_db"] == tmp_path / "semantic" / "semantic.db"

    def test_other_keys_unchanged(self, tmp_path: Path) -> None:
        """The fix must not perturb the other live_dirs keys."""
        out = _live_dirs_from(tmp_path)
        assert out["skills_db"] == tmp_path / "skills" / "skills_index.db"
        assert out["skills_dir_path"] == tmp_path / "skills"
        assert out["episodes_db"] == tmp_path / "episodes" / "episodes.db"
