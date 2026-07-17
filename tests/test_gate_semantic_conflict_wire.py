"""Wiring of the (previously dormant) semantic_conflict moat into the write gate.

detect_semantic_conflicts was built + benchmarked but had NO live caller. It is now
wired into run_validation_gate's full path behind ENGRAM_SEMANTIC_CONFLICT (default
OFF — it adds an LLM judgement per same-topic sibling, so the lexical default path is
unchanged). These tests assert the WIRING (the detector itself is covered by
test_semantic_conflict); detect_semantic_conflicts is stubbed so no e5 / no claude.
"""
from __future__ import annotations

import types

import pytest

from verimem import anti_confab_gate, semantic_conflict
from verimem.coherence_check import CoherenceWarning


class _StubSemantic:
    def all(self):
        return [types.SimpleNamespace(id="sib1", proposition="x", topic="t")]


class _StubLLM:
    def complete(self, *a, **k):
        return types.SimpleNamespace(text="NEUTRAL")


class _StubAgent:
    def __init__(self) -> None:
        self.llm = _StubLLM()
        self.semantic = _StubSemantic()


def _gate(**over):
    kw = dict(proposition="some claim", verified_by=None, topic="t",
              agent=_StubAgent(), validate="full")
    kw.update(over)
    return anti_confab_gate.run_validation_gate(**kw)


def test_off_by_default_detector_not_called(monkeypatch):
    monkeypatch.delenv("ENGRAM_SEMANTIC_CONFLICT", raising=False)
    called = {"n": 0}

    def _spy(*a, **k):
        called["n"] += 1
        return []
    monkeypatch.setattr(semantic_conflict, "detect_semantic_conflicts", _spy)
    res = _gate()
    assert called["n"] == 0           # no LLM/detector cost on the default path
    assert res.action == "persist"


def test_on_contradiction_escalates_to_downgrade(monkeypatch):
    monkeypatch.setenv("ENGRAM_SEMANTIC_CONFLICT", "1")
    monkeypatch.setattr(
        semantic_conflict, "detect_semantic_conflicts",
        lambda *a, **k: [CoherenceWarning(
            kind="semantic_conflict", other_fact_id="sib1", details="nli=contradiction")],
    )
    res = _gate()
    assert res.action == "downgrade"
    assert any(w.get("layer") == "L3-semantic" for w in res.warnings)
    assert "sib1" in res.contradicting_fact_ids


def test_on_contradiction_reject_mode_blocks(monkeypatch):
    monkeypatch.setenv("ENGRAM_SEMANTIC_CONFLICT", "1")
    monkeypatch.setattr(
        semantic_conflict, "detect_semantic_conflicts",
        lambda *a, **k: [CoherenceWarning(
            kind="semantic_conflict", other_fact_id="sib1")],
    )
    res = _gate(gate_mode="reject")
    assert res.action == "reject"


def test_on_neutral_persists(monkeypatch):
    monkeypatch.setenv("ENGRAM_SEMANTIC_CONFLICT", "1")
    monkeypatch.setattr(semantic_conflict, "detect_semantic_conflicts",
                        lambda *a, **k: [])
    res = _gate()
    assert res.action == "persist"


def test_on_but_no_llm_is_graceful(monkeypatch):
    monkeypatch.setenv("ENGRAM_SEMANTIC_CONFLICT", "1")
    called = {"n": 0}
    monkeypatch.setattr(semantic_conflict, "detect_semantic_conflicts",
                        lambda *a, **k: called.__setitem__("n", called["n"] + 1) or [])
    agent = _StubAgent()
    agent.llm = None  # no judge available
    res = anti_confab_gate.run_validation_gate(
        proposition="some claim", verified_by=None, topic="t",
        agent=agent, validate="full")
    assert called["n"] == 0 and res.action == "persist"  # skipped, no crash
