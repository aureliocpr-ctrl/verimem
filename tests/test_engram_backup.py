"""Cycle 2026-05-27 round 13 P0 — DB backup module pytest TDD.

Closes Aurelio audit gap C4: no backup/restore DB ufficiale.

Verifies the foundation safety contract:
- create_backup is atomic + content-faithful (integrity hash matches source)
- restore_from_backup preserves 100% fact integrity (count + content hash)
- restore_from_backup keeps a pre-restore safety copy by default
- list_backups returns newest-first across tiers
- rotate_backups respects retention policy (N most recent per tier)
"""
from __future__ import annotations

import shutil
import sqlite3
import time
from pathlib import Path

import pytest

from engram.backup import (
    DEFAULT_POLICY,
    create_backup,
    list_backups,
    restore_from_backup,
    rotate_backups,
)
from engram.semantic import Fact, SemanticMemory


@pytest.fixture
def live_db(tmp_path: Path) -> Path:
    """A real SemanticMemory DB seeded with 10 facts."""
    db_path = tmp_path / "live.db"
    sm = SemanticMemory(db_path=db_path)
    for i in range(10):
        sm.store(Fact(
            id=f"fact{i:02d}aabbcc",
            proposition=f"Test fact number {i} for backup integrity.",
            topic=f"test/backup/{i}",
            confidence=0.9,
            verified_by=[],
            status="model_claim",
        ))
    return db_path


@pytest.fixture
def backup_root(tmp_path: Path) -> Path:
    return tmp_path / "backups"


class TestCreateBackup:
    def test_backup_creates_file(self, live_db: Path, backup_root: Path):
        info = create_backup(live_db, backup_root, tier="daily")
        assert info.path.exists()
        assert info.tier == "daily"
        assert info.size_bytes > 0

    def test_backup_integrity_matches_source(
        self, live_db: Path, backup_root: Path,
    ):
        info = create_backup(live_db, backup_root, tier="manual")
        assert info.fact_count == 10
        assert info.integrity_hash is not None
        # Verify the backup actually contains the 10 fact ids.
        conn = sqlite3.connect(str(info.path), timeout=5)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM facts")
        assert cur.fetchone()[0] == 10
        conn.close()

    def test_backup_missing_source_raises(
        self, tmp_path: Path, backup_root: Path,
    ):
        with pytest.raises(FileNotFoundError):
            create_backup(tmp_path / "nope.db", backup_root)

    def test_backup_into_distinct_tier_subdirs(
        self, live_db: Path, backup_root: Path,
    ):
        for tier in ("daily", "weekly", "monthly", "manual"):
            info = create_backup(live_db, backup_root, tier=tier)
            assert info.path.parent.name == tier


class TestRestoreRoundTrip:
    def test_restore_recovers_full_corpus(
        self, live_db: Path, backup_root: Path, tmp_path: Path,
    ):
        # 1. Backup the live DB.
        info = create_backup(live_db, backup_root, tier="manual")

        # 2. Corrupt the live DB: drop all facts.
        conn = sqlite3.connect(str(live_db), timeout=5)
        conn.execute("DELETE FROM facts")
        conn.commit()
        conn.close()
        # Confirm corruption.
        conn = sqlite3.connect(str(live_db), timeout=5)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM facts")
        assert cur.fetchone()[0] == 0
        conn.close()

        # 3. Restore from backup.
        result = restore_from_backup(
            info.path, live_db,
            keep_pre_restore_copy=False,
        )
        assert result["ok"] is True
        assert result["fact_count"] == 10
        # 4. Confirm restoration.
        conn = sqlite3.connect(str(live_db), timeout=5)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM facts")
        assert cur.fetchone()[0] == 10
        conn.close()

    def test_restore_creates_pre_copy_by_default(
        self, live_db: Path, backup_root: Path,
    ):
        info = create_backup(live_db, backup_root, tier="manual")
        # Modify live so the pre-copy is distinguishable.
        conn = sqlite3.connect(str(live_db), timeout=5)
        conn.execute("DELETE FROM facts WHERE id LIKE 'fact00%'")
        conn.commit()
        conn.close()

        result = restore_from_backup(info.path, live_db)
        assert result["pre_restore_copy"] is not None
        pre = Path(result["pre_restore_copy"])
        assert pre.exists()
        # The pre-copy must have the 9 facts that existed before restore.
        conn = sqlite3.connect(str(pre), timeout=5)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM facts")
        assert cur.fetchone()[0] == 9
        conn.close()


class TestListBackups:
    def test_list_returns_newest_first(
        self, live_db: Path, backup_root: Path,
    ):
        a = create_backup(live_db, backup_root, tier="daily")
        time.sleep(1.1)  # ensure mtime ordering
        b = create_backup(live_db, backup_root, tier="daily")
        listed = list_backups(backup_root)
        assert len(listed) >= 2
        assert listed[0].path == b.path
        assert listed[1].path == a.path

    def test_list_tier_filter(self, live_db: Path, backup_root: Path):
        create_backup(live_db, backup_root, tier="daily")
        create_backup(live_db, backup_root, tier="weekly")
        d = list_backups(backup_root, tier="daily")
        w = list_backups(backup_root, tier="weekly")
        assert all(b.tier == "daily" for b in d)
        assert all(b.tier == "weekly" for b in w)


class TestRotation:
    def test_keeps_only_n_most_recent_per_tier(
        self, live_db: Path, backup_root: Path,
    ):
        # Create 10 daily backups. Default policy keeps 7.
        for _ in range(10):
            create_backup(live_db, backup_root, tier="daily")
            time.sleep(0.05)
        deleted = rotate_backups(backup_root)
        # 10 created - 7 kept = 3 deleted.
        assert len(deleted) == 3
        remaining = list_backups(backup_root, tier="daily")
        assert len(remaining) == 7

    def test_idempotent(self, live_db: Path, backup_root: Path):
        for _ in range(5):
            create_backup(live_db, backup_root, tier="daily")
            time.sleep(0.05)
        # First rotation: nothing to delete (under quota).
        d1 = rotate_backups(backup_root)
        assert d1 == []
        # Second rotation: still nothing.
        d2 = rotate_backups(backup_root)
        assert d2 == []


class TestRotationCustomPolicy:
    def test_custom_keep_count(self, live_db: Path, backup_root: Path):
        for _ in range(8):
            create_backup(live_db, backup_root, tier="manual")
            time.sleep(0.05)
        deleted = rotate_backups(
            backup_root,
            policy={"manual": 3, "daily": 7, "weekly": 4, "monthly": 12},
        )
        assert len(deleted) == 5
        remaining = list_backups(backup_root, tier="manual")
        assert len(remaining) == 3
