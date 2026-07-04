"""TDD — bench_self_model_ab: opt-in + auto-recovery (scan 68-Opus medium [46]).
Bug: lo script (NON pytest, __main__) rinomina il self_model.db REALE; il
restore e' in un finally ma un crash HARD (kill -9/segfault) lo bypassa ->
DB di sistema lasciato come .bench_backup. Fix: guard HIPPO_ALLOW_REAL_BENCH=1
(no run accidentali) + _recover_from_crash() che ripristina all'avvio.
Test HERMETIC: monkeypatch attr modulo su path tmp, no ~/.engram, no claude."""
from __future__ import annotations

import importlib
from pathlib import Path

m = importlib.import_module("tests.perf.bench_self_model_ab")


def test_main_skips_without_optin(monkeypatch):
    called = {"claude": 0}
    monkeypatch.delenv("HIPPO_ALLOW_REAL_BENCH", raising=False)
    monkeypatch.setattr(m, "_run_claude", lambda *a, **k: called.__setitem__("claude", called["claude"] + 1))
    rc = m.main()
    assert rc == 0, "senza opt-in main() deve uscire 0 (skip)"
    assert called["claude"] == 0, "senza opt-in NON deve lanciare claude / toccare il DB"


def test_recover_from_crash_restores_renamed_db(monkeypatch, tmp_path):
    real = tmp_path / "self_model.db"
    backup = tmp_path / "self_model.db.bench_backup"
    backup.write_text("DB content da un run crashato")  # reale assente, backup presente
    monkeypatch.setattr(m, "SELF_MODEL_DB", real)
    monkeypatch.setattr(m, "BACKUP_DB", backup)

    recovered = m._recover_from_crash()

    assert recovered is True
    assert real.exists() and real.read_text() == "DB content da un run crashato"
    assert not backup.exists(), "il backup deve essere stato spostato sul reale"


def test_recover_noop_when_real_present(monkeypatch, tmp_path):
    real = tmp_path / "self_model.db"
    backup = tmp_path / "self_model.db.bench_backup"
    real.write_text("reale ok")
    backup.write_text("stale backup")
    monkeypatch.setattr(m, "SELF_MODEL_DB", real)
    monkeypatch.setattr(m, "BACKUP_DB", backup)

    assert m._recover_from_crash() is False, "se il reale c'e', non recuperare"
    assert real.read_text() == "reale ok", "il reale NON deve essere sovrascritto"
