"""audit#3-r3 R16: create_backup verified integrity by re-reading the LIVE db
and comparing it to the VACUUM-INTO snapshot. A writer committing BETWEEN the
snapshot and that re-read made source != backup, so a perfectly good backup was
DELETED and a RuntimeError raised — a false positive driven by a moving target.

Fix: validate the SNAPSHOT's own integrity (readable + PRAGMA integrity_check +
expected table), never equality with the live (moving) source.
"""
from __future__ import annotations

from pathlib import Path

from engram import backup as bk
from engram.semantic import Fact, SemanticMemory


def test_concurrent_source_write_does_not_delete_good_backup(tmp_path, monkeypatch):
    src = tmp_path / "semantic.db"
    sm = SemanticMemory(db_path=src)
    sm.store(Fact(proposition="keep this backup", topic="t", source_episodes=["e"]))

    real = bk._compute_integrity_hash

    def fake(path, table="facts"):
        c, h = real(path, table)
        if Path(path).resolve() == src.resolve():
            # Simulate a writer that commits AFTER the VACUUM snapshot: the LIVE
            # source now reads differently than the (valid) snapshot.
            return c + 1, "live-moved-on-" + h
        return c, h

    monkeypatch.setattr(bk, "_compute_integrity_hash", fake)

    info = bk.create_backup(src, tmp_path / "bk", tier="manual")
    assert Path(info.path).exists(), (
        "create_backup deleted a valid snapshot because the LIVE source changed "
        "after the VACUUM — integrity must validate the snapshot itself"
    )
    assert info.fact_count == 1


def test_create_backup_happy_path_records_hash(tmp_path):
    src = tmp_path / "semantic.db"
    sm = SemanticMemory(db_path=src)
    sm.store(Fact(proposition="p", topic="t", source_episodes=["e"]))
    info = bk.create_backup(src, tmp_path / "bk", tier="manual")
    assert Path(info.path).exists()
    assert info.fact_count == 1
    assert info.integrity_hash
