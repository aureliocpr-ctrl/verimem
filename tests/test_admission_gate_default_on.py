"""0.7.0 flip: the admission gate is ON out of the box.

Decision record (2026-07-20, adversarial review GLM-5.2 + Kimi-K3, both
independent, convergent):
  - The measured pre-gate corpus trajectory (75% quarantined, 94% of it
    machine exhaust) is what any unprotected deployment drifts toward; a
    "verified memory" that admits machine exhaust as curated facts by
    default is a false claim. Hence default ON.
  - The flip must not be silent ("memory that decides for you without
    telling you is the opposite of verified memory" — Kimi): the first
    routed write in a process where the operator made NO explicit choice
    emits a one-time migration warning naming the opt-out.
  - An explicit choice (env set to any recognized value) means no
    migration warning: the operator already decided.
  - Content-based classification (JSON-shape sniffing) was REJECTED by
    both reviewers (false positives without undo, e.g. a calendar entry
    {"event_type": "dentist", ...}); routing stays topic-prefix only.
"""
from __future__ import annotations

import sqlite3
import warnings

import pytest

from verimem.semantic import Fact, SemanticMemory


def _count(db, sql):
    c = sqlite3.connect(db)
    try:
        return c.execute(sql).fetchone()[0]
    finally:
        c.close()


def _no_explicit_choice(monkeypatch):
    monkeypatch.delenv("ENGRAM_ADMISSION_GATE", raising=False)


def test_gate_on_by_default(monkeypatch, tmp_path):
    _no_explicit_choice(monkeypatch)
    import dataclasses

    import verimem.config as cfg
    monkeypatch.setattr(
        cfg, "CONFIG", dataclasses.replace(cfg.CONFIG, data_dir=str(tmp_path)))
    from verimem.admission_gate import gate_enabled
    assert gate_enabled() is True


@pytest.mark.parametrize("off", ["0", "off", "false", "no"])
def test_gate_explicit_off_wins(monkeypatch, off):
    monkeypatch.setenv("ENGRAM_ADMISSION_GATE", off)
    from verimem.admission_gate import gate_enabled
    assert gate_enabled() is False


@pytest.mark.parametrize("on", ["1", "on", "true", "strict"])
def test_gate_explicit_on_still_on(monkeypatch, on):
    monkeypatch.setenv("ENGRAM_ADMISSION_GATE", on)
    from verimem.admission_gate import gate_enabled
    assert gate_enabled() is True


def test_store_routes_telemetry_by_default(tmp_path, monkeypatch):
    _no_explicit_choice(monkeypatch)
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    sm.store(Fact(proposition="ambient daemon event fired", topic="bus/ambient"))
    db = tmp_path / "s.db"
    assert _count(db, "SELECT COUNT(*) FROM facts WHERE topic LIKE 'bus/%'") == 0
    assert _count(db, "SELECT COUNT(*) FROM telemetry") == 1


def test_store_legacy_behavior_with_explicit_optout(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGRAM_ADMISSION_GATE", "0")
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    sm.store(Fact(proposition="ambient daemon event fired", topic="bus/ambient"))
    assert _count(
        tmp_path / "s.db",
        "SELECT COUNT(*) FROM facts WHERE topic LIKE 'bus/%'") == 1


def test_first_route_without_explicit_choice_warns_once(tmp_path, monkeypatch):
    _no_explicit_choice(monkeypatch)
    import verimem.admission_gate as ag
    monkeypatch.setattr(ag, "_MIGRATION_WARNED", False)
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        sm.store(Fact(proposition="tick 1", topic="metric/cpu"))
        sm.store(Fact(proposition="tick 2", topic="metric/cpu2"))
    migration = [w for w in caught
                 if "ENGRAM_ADMISSION_GATE" in str(w.message)]
    assert len(migration) == 1, (
        "exactly one migration warning for the whole process, naming the "
        f"opt-out env var; got {len(migration)}")
    assert "telemetry" in str(migration[0].message).lower()


def test_no_migration_warning_when_choice_is_explicit(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGRAM_ADMISSION_GATE", "1")
    import verimem.admission_gate as ag
    monkeypatch.setattr(ag, "_MIGRATION_WARNED", False)
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        sm.store(Fact(proposition="tick", topic="metric/cpu"))
    assert not [w for w in caught
                if "ENGRAM_ADMISSION_GATE" in str(w.message)]
