"""Audit#2 2026-06-08 A-9: backup/restore only covered semantic.db — the
integrity check hardcoded `SELECT ... FROM facts`, so create_backup on
episodes.db / skills_index.db raised 'no such table: facts', and the only CLI
caller (`engram facts backup`) was facts-scoped. A disaster-restore therefore
silently lost every episode and skill. Fix: parametrize the integrity table and
add create_all_backups() covering all three stores.
"""
from __future__ import annotations

from verimem.backup import BackupInfo, create_all_backups, create_backup, restore_from_backup
from verimem.memory import EpisodicMemory
from verimem.semantic import Fact, SemanticMemory
from verimem.skill import SkillLibrary


def _make_dbs(d):
    se, ep, sk = d / "se.db", d / "ep.db", d / "sk.db"
    sm = SemanticMemory(db_path=se)
    sm.store(Fact(proposition="p1", topic="t", status="model_claim",
                  source_episodes=["e"]), embed="defer")
    EpisodicMemory(db_path=ep)   # schema created; rows optional for the gap
    SkillLibrary(db_path=sk)
    return se, ep, sk


def test_create_backup_handles_non_facts_db(tmp_path):
    # episodes.db has no `facts` table — pre-fix this raised OperationalError
    # under the default verify (the A-9 bug). With integrity_table it verifies
    # against its own primary table.
    ep = tmp_path / "ep.db"
    EpisodicMemory(db_path=ep)
    info = create_backup(ep, tmp_path / "bk", tier="manual",
                         integrity_table="episodes")
    assert isinstance(info, BackupInfo)
    assert info.integrity_hash is not None
    assert info.path.exists()


def test_create_all_backups_covers_all_three_stores(tmp_path):
    se, ep, sk = _make_dbs(tmp_path / "data")
    res = create_all_backups(
        semantic_db=se, episodes_db=ep, skills_db=sk,
        backup_root=tmp_path / "bk", tier="manual",
    )
    for name in ("semantic", "episodes", "skills"):
        assert isinstance(res[name], BackupInfo), f"{name} not backed up: {res[name]}"
        assert res[name].path.exists()
    # The gap proven closed: round-trip restore the EPISODES backup, verified
    # against its own primary table.
    out = restore_from_backup(
        res["episodes"].path, tmp_path / "restored_ep.db",
        integrity_table="episodes", keep_pre_restore_copy=False,
    )
    assert out["ok"] is True


def test_create_all_backups_records_missing_db_without_aborting(tmp_path):
    se, ep, _ = _make_dbs(tmp_path / "data")
    res = create_all_backups(
        semantic_db=se, episodes_db=ep, skills_db=tmp_path / "data" / "nope.db",
        backup_root=tmp_path / "bk", tier="manual",
    )
    assert isinstance(res["semantic"], BackupInfo)
    assert isinstance(res["episodes"], BackupInfo)
    assert isinstance(res["skills"], dict) and res["skills"]["ok"] is False
