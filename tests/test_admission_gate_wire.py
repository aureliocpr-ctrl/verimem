"""Wire of the admission gate into SemanticMemory.store.

Since 0.7.0 the gate is ON by default (see test_admission_gate_default_on.py
for the flip's decision record): telemetry-topic writes are routed to a
separate `telemetry` table, NON-lossy; real facts unaffected + recallable.
ENGRAM_ADMISSION_GATE=0 restores the legacy admit-everything behavior.
Hermetic: tmp DB, monkeypatched env, never ~/.verimem.
"""
from __future__ import annotations

import sqlite3

from verimem.semantic import Fact, SemanticMemory


def _count(db, sql):
    c = sqlite3.connect(db)
    try:
        return c.execute(sql).fetchone()[0]
    finally:
        c.close()


def test_gate_off_keeps_telemetry_in_facts(tmp_path, monkeypatch):
    # 0.7.0: legacy behavior needs the EXPLICIT opt-out (default is ON now)
    monkeypatch.setenv("ENGRAM_ADMISSION_GATE", "0")
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    sm.store(Fact(proposition="ambient daemon event fired xyz", topic="bus/ambient/events"))
    # legacy behavior: telemetry is just a normal fact
    assert _count(tmp_path / "s.db", "SELECT COUNT(*) FROM facts WHERE topic LIKE 'bus/%'") == 1


def test_gate_on_routes_telemetry_out_of_facts_nonlossy(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGRAM_ADMISSION_GATE", "1")
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    sm.store(Fact(proposition="ambient daemon event fired xyz", topic="bus/ambient/events"))
    sm.store(Fact(proposition="we decided to adopt e5-base for recall", topic="decisions/embedding",
                  status="model_claim", source_episodes=["ep1"]))
    db = tmp_path / "s.db"
    assert _count(db, "SELECT COUNT(*) FROM facts WHERE topic LIKE 'bus/%'") == 0, "telemetry leaked into curated facts"
    assert _count(db, "SELECT COUNT(*) FROM telemetry") == 1, "telemetry not preserved (lossy!)"
    assert _count(db, "SELECT COUNT(*) FROM facts WHERE topic='decisions/embedding'") == 1, "real fact wrongly routed"


def test_gate_on_real_fact_still_recallable(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGRAM_ADMISSION_GATE", "1")
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    sm.store(Fact(proposition="the e5-base model improved retrieval recall a lot",
                  topic="decisions/embedding", source_episodes=["ep1"]))
    sm.store(Fact(proposition="noise telemetry tick", topic="metric/cpu"))
    hits = sm.recall("e5-base retrieval recall", k=5)
    assert any("e5-base" in f.proposition for f, *_ in hits), "real fact not recallable under gate ON"
    # the metric/ telemetry must NOT appear in recall
    assert not any("telemetry tick" in f.proposition for f, *_ in hits)


def _patch_data_dir(monkeypatch, tmp_path):
    """CONFIG is a frozen dataclass -> use dataclasses.replace + patch the module
    attribute (gate_enabled does `from .config import CONFIG` at call time)."""
    import dataclasses

    import verimem.config as cfg
    monkeypatch.setattr(cfg, "CONFIG", dataclasses.replace(cfg.CONFIG, data_dir=str(tmp_path)))


def test_gate_enabled_contract_0_7(tmp_path, monkeypatch):
    # 0.7.0 contract: default ON; explicit env always wins; the pre-0.7.0
    # ADMISSION_GATE_ON flag file is obsolete and IGNORED (it could only
    # force ON — which the default now is — and must not defeat an
    # explicit operator OFF).
    from verimem.admission_gate import gate_enabled
    monkeypatch.delenv("ENGRAM_ADMISSION_GATE", raising=False)
    _patch_data_dir(monkeypatch, tmp_path)
    assert gate_enabled() is True   # default ON, no env, no file
    monkeypatch.setenv("ENGRAM_ADMISSION_GATE", "1")
    assert gate_enabled() is True
    monkeypatch.setenv("ENGRAM_ADMISSION_GATE", "0")
    assert gate_enabled() is False  # explicit OFF wins
    (tmp_path / "ADMISSION_GATE_ON").write_text("")
    assert gate_enabled() is False, "a stale flag file must not defeat an explicit OFF"


def test_store_routes_with_no_env_and_no_flag_file(tmp_path, monkeypatch):
    monkeypatch.delenv("ENGRAM_ADMISSION_GATE", raising=False)
    _patch_data_dir(monkeypatch, tmp_path)
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    sm.store(Fact(proposition="ambient bus event via default", topic="bus/x/y"))
    sm.store(Fact(proposition="real fact about retrieval", topic="decisions/x", source_episodes=["ep1"]))
    assert _count(tmp_path / "s.db", "SELECT COUNT(*) FROM facts WHERE topic LIKE 'bus/%'") == 0
    assert _count(tmp_path / "s.db", "SELECT COUNT(*) FROM telemetry") == 1
    assert _count(tmp_path / "s.db", "SELECT COUNT(*) FROM facts WHERE topic='decisions/x'") == 1
