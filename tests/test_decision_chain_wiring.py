"""Decision-chain wiring into Memory (task #15) — TDD.

Memory.record_decision / why_decision / decision_outcome delegate to a
DecisionStore on a sibling DB (decisions.db next to semantic.db, the
documents.py sibling-path pattern). Lazy: the store/file appears only once a
decision is recorded.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from verimem.client import Memory


def test_record_and_why_through_memory(tmp_path):
    mem = Memory(tmp_path / "m.db")
    did = mem.record_decision(
        "Adopt the self-calibrating relevance floor",
        alternatives=["hardcode tau=0.80"],
        evidence=["fact_floor_bench"],
        expected="external false_answer < 0.10",
        topic="decisions/read-path")
    assert did
    hits = mem.why_decision("why did we choose the self-calibrating floor?")
    assert hits and hits[0]["evidence"] == ["fact_floor_bench"]
    assert hits[0]["id"] == did


def test_decision_store_is_a_sibling_db(tmp_path):
    mem = Memory(tmp_path / "m.db")
    mem.record_decision("x", topic="decisions/t")
    assert (tmp_path / "decisions.db").exists(), (
        "decisions live in a sibling DB, never in semantic.db")


def test_outcome_requires_evidence_through_memory(tmp_path):
    mem = Memory(tmp_path / "m.db")
    did = mem.record_decision("Ship the sim-fallback", topic="decisions/r")
    with pytest.raises(ValueError):
        mem.decision_outcome(did, "worked", verified_by=[])
    assert mem.decision_outcome(
        did, "mini-world stale 0.63->0.10",
        verified_by=["bench:source_trust_miniworld:seed11"])


def test_why_decision_empty_when_none_recorded(tmp_path):
    mem = Memory(tmp_path / "m.db")
    assert mem.why_decision("why anything?") == []
    assert not (tmp_path / "decisions.db").exists(), (
        "a pure read must not create the store file")
