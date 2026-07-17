"""P1 (audit 2026-06-07): SemanticMemory.store() must HONOR the admission-gate
verdict, not only ROUTE_TELEMETRY.

Pre-fix, store() acted on ROUTE_TELEMETRY alone; REJECT_POLLUTED (leaked
tool-call markup) and FLAG_INJECTION fell through and entered the curated
corpus despite the gate flagging them. Fix: anything the gate refuses to admit
(admit_to_curated=False) is QUARANTINED (non-lossy — rank -1, hidden from
default recall, kept for audit), mirroring the injection screen. The gate is
opt-in (ENGRAM_ADMISSION_GATE) so default installs are byte-identical.

Hermetic: tmp DB, embed='defer', monkeypatched env. The injection screen is
turned OFF to isolate the gate's own decision.
"""
from __future__ import annotations

import sqlite3

from verimem.semantic import Fact, SemanticMemory


def _status(db, like: str):
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        r = c.execute(
            "SELECT status FROM facts WHERE proposition LIKE ?", (like,)
        ).fetchone()
        return r[0] if r else None
    finally:
        c.close()


def test_gate_quarantines_polluted_when_enabled(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("ENGRAM_ADMISSION_GATE", "1")
    monkeypatch.setenv("ENGRAM_INJECTION_SCREEN", "0")  # isolate the gate decision
    monkeypatch.delenv("ENGRAM_REDACT_SECRETS", raising=False)
    db = tmp_path / "s.db"
    sm = SemanticMemory(db_path=db)
    sm.store(
        Fact(proposition='leaked <parameter name="cmd">x</parameter> tool markup',
             topic="proj/x", status="model_claim", source_episodes=["ep1"]),
        embed="defer",
    )
    assert _status(db, "leaked%") == "quarantined"


def test_gate_admits_clean_grounded_fact(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("ENGRAM_ADMISSION_GATE", "1")
    monkeypatch.setenv("ENGRAM_INJECTION_SCREEN", "0")
    db = tmp_path / "s.db"
    sm = SemanticMemory(db_path=db)
    sm.store(
        Fact(proposition="the capital of France is Paris", topic="geo/fr",
             status="model_claim", source_episodes=["ep1"]),
        embed="defer",
    )
    assert _status(db, "the capital%") != "quarantined"


def test_gate_off_leaves_polluted_unquarantined(tmp_path, monkeypatch) -> None:
    # Gate OFF (default) -> legacy behavior; the gate takes no action. Proves the
    # fix is opt-in and default installs are unaffected.
    monkeypatch.delenv("ENGRAM_ADMISSION_GATE", raising=False)
    monkeypatch.setenv("ENGRAM_INJECTION_SCREEN", "0")
    db = tmp_path / "s.db"
    sm = SemanticMemory(db_path=db)
    sm.store(
        Fact(proposition='gateoff <parameter name="c">x</parameter> markup',
             topic="proj/y", status="model_claim", source_episodes=["ep1"]),
        embed="defer",
    )
    assert _status(db, "gateoff%") != "quarantined"
