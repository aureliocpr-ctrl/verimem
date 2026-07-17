"""Wire of the admission gate into SemanticMemory.store (opt-in, default OFF).

Default OFF -> byte-identical legacy behavior (telemetry stays a normal fact).
ON (ENGRAM_ADMISSION_GATE=1) -> telemetry-topic writes routed to a separate
`telemetry` table, NON-lossy; real facts unaffected + still recallable.
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
    monkeypatch.delenv("ENGRAM_ADMISSION_GATE", raising=False)
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


def test_gate_enabled_env_or_flag_file(tmp_path, monkeypatch):
    from verimem.admission_gate import gate_enabled
    monkeypatch.delenv("ENGRAM_ADMISSION_GATE", raising=False)
    _patch_data_dir(monkeypatch, tmp_path)
    assert gate_enabled() is False
    monkeypatch.setenv("ENGRAM_ADMISSION_GATE", "1")
    assert gate_enabled() is True
    monkeypatch.delenv("ENGRAM_ADMISSION_GATE", raising=False)
    (tmp_path / "ADMISSION_GATE_ON").write_text("")
    assert gate_enabled() is True  # file-flag alone enables


def test_store_enabled_via_flag_file_no_env(tmp_path, monkeypatch):
    monkeypatch.delenv("ENGRAM_ADMISSION_GATE", raising=False)
    _patch_data_dir(monkeypatch, tmp_path)
    (tmp_path / "ADMISSION_GATE_ON").write_text("")  # enable via FILE only
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    sm.store(Fact(proposition="ambient bus event via flag", topic="bus/x/y"))
    sm.store(Fact(proposition="real fact about retrieval", topic="decisions/x", source_episodes=["ep1"]))
    assert _count(tmp_path / "s.db", "SELECT COUNT(*) FROM facts WHERE topic LIKE 'bus/%'") == 0
    assert _count(tmp_path / "s.db", "SELECT COUNT(*) FROM telemetry") == 1
    assert _count(tmp_path / "s.db", "SELECT COUNT(*) FROM facts WHERE topic='decisions/x'") == 1
