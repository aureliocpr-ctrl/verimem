"""audit#3-r3 R5: ``engram facts restore`` (restore_from_backup) must REFUSE a
backup that lacks the expected primary table BEFORE overwriting the target.

Pre-fix the SQLite ``.backup()`` copy replaced every page of semantic.db first,
and only THEN did ``_compute_integrity_hash(target, "facts")`` run — so handing
``facts restore`` an episodes/skills backup (no ``facts`` table) silently
corrupted the live facts DB and raised ``OperationalError`` after the damage.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from verimem.backup import create_backup, restore_from_backup
from verimem.semantic import Fact, SemanticMemory


def test_restore_refuses_wrong_store_backup_and_leaves_target_intact(tmp_path):
    target = tmp_path / "semantic.db"
    sm = SemanticMemory(db_path=target)
    sm.store(Fact(proposition="keep me alive", topic="t", source_episodes=["e"]))

    # A wrong-store backup: looks like an episodes DB, has NO `facts` table.
    wrong = tmp_path / "episodes_like.db"
    c = sqlite3.connect(str(wrong))
    c.execute("CREATE TABLE episodes(id TEXT)")
    c.execute("INSERT INTO episodes VALUES ('x')")
    c.commit()
    c.close()

    with pytest.raises(ValueError):
        restore_from_backup(wrong, target)

    # The target's facts must survive — the restore must abort pre-overwrite.
    fresh = SemanticMemory(db_path=target)
    props = [f.proposition for f in fresh.all()]
    assert "keep me alive" in props, (
        "wrong-store restore corrupted semantic.db: facts were lost"
    )


def test_restore_still_accepts_a_real_facts_backup(tmp_path):
    """The guard must NOT block a legitimate facts backup (round-trip works)."""
    src_db = tmp_path / "src_semantic.db"
    sm = SemanticMemory(db_path=src_db)
    sm.store(Fact(proposition="restored content", topic="t", source_episodes=["e"]))
    binfo = create_backup(src_db, tmp_path / "bk", tier="manual")

    target = tmp_path / "target_semantic.db"
    SemanticMemory(db_path=target)  # materialize an empty target with schema

    out = restore_from_backup(Path(binfo.path), target)
    assert out["ok"] is True
    fresh = SemanticMemory(db_path=target)
    assert "restored content" in [f.proposition for f in fresh.all()]
