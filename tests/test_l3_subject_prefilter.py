"""L3-semantic subject pre-filter wiring (P2, env-gated, DEFAULT OFF).

The NLI judge over-flags contradictions on DIFFERENT-subject pairs (the cosine
0.7 pre-filter is inert — 595/595 pairs clear it). ENGRAM_L3_SUBJECT_FILTER=1
filters the sibling list by verimem.subject_extract.same_subject BEFORE the
NLI judge sees it: different-subject siblings never reach the judge (kills the
FP class + saves judge budget); same-subject and UNATTRIBUTABLE (pronoun/empty
subject) siblings still reach it (fail-open — a conflict we cannot attribute
must still be judged). Default OFF: sibling list byte-identical.

These tests assert the WIRING: detect_semantic_conflicts is stubbed with a spy
that records the sibling list it receives (idiom of test_gate_semantic_conflict
_wire.py — no e5, no claude, no NLI model).
"""
from __future__ import annotations

import types

import pytest

from verimem import anti_confab_gate, semantic_conflict
from verimem.coherence_check import CoherenceWarning

CANDIDATE = "The Rossi SpA contract expires on 31 January 2027."
SIB_SAME = "The Rossi SpA contract expires in 2025."
SIB_DIFF = "The invoice total is 12,450 euros."


class _StubSemantic:
    def __init__(self, props):
        self._props = props

    def all(self):
        return [types.SimpleNamespace(id=f"sib{i}", proposition=p, topic="t")
                for i, p in enumerate(self._props)]


class _StubLLM:
    def complete(self, *a, **k):  # never consulted: detector is stubbed
        return types.SimpleNamespace(text="NEUTRAL")


def _agent(props):
    a = types.SimpleNamespace()
    a.llm = _StubLLM()
    a.semantic = _StubSemantic(props)
    return a


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("ENGRAM_SEMANTIC_CONFLICT", "1")
    monkeypatch.delenv("ENGRAM_L3_SUBJECT_FILTER", raising=False)
    yield


def _spy(monkeypatch):
    """Stub the detector; record the sibling propositions it receives and flag
    every one of them as a contradiction (worst-case judge)."""
    seen: list[list[str]] = []

    def _fake(new, sibs, judge):
        sib_list = list(sibs)
        seen.append([getattr(s, "proposition", "") for s in sib_list])
        return [CoherenceWarning(kind="semantic_conflict",
                                 other_fact_id=getattr(s, "id", ""))
                for s in sib_list]
    monkeypatch.setattr(semantic_conflict, "detect_semantic_conflicts", _fake)
    return seen


def _gate(props, proposition=CANDIDATE):
    return anti_confab_gate.run_validation_gate(
        proposition=proposition, verified_by=None, topic="t",
        agent=_agent(props), validate="full")


def test_off_by_default_sibling_list_unfiltered(monkeypatch):
    seen = _spy(monkeypatch)
    res = _gate([SIB_DIFF, SIB_SAME])
    assert seen and set(seen[0]) == {SIB_DIFF, SIB_SAME}
    assert any(w.get("layer") == "L3-semantic" for w in res.warnings)


def test_on_different_subject_sibling_never_reaches_judge(monkeypatch):
    monkeypatch.setenv("ENGRAM_L3_SUBJECT_FILTER", "1")
    seen = _spy(monkeypatch)
    res = _gate([SIB_DIFF])
    assert seen == [[]] or seen == []          # judge saw NO different-subject sib
    assert not any(str(w.get("layer", "")).startswith("L3-semantic")
                   for w in res.warnings)
    assert res.action == "persist"


def test_on_same_subject_sibling_still_judged(monkeypatch):
    monkeypatch.setenv("ENGRAM_L3_SUBJECT_FILTER", "1")
    seen = _spy(monkeypatch)
    res = _gate([SIB_DIFF, SIB_SAME])
    assert seen and seen[0] == [SIB_SAME]      # filtered to the same-subject one
    assert any(w.get("layer") == "L3-semantic" for w in res.warnings)


def test_on_unattributable_candidate_fails_open(monkeypatch):
    monkeypatch.setenv("ENGRAM_L3_SUBJECT_FILTER", "1")
    seen = _spy(monkeypatch)
    _gate([SIB_DIFF], proposition="It was completed on Tuesday.")
    assert seen and seen[0] == [SIB_DIFF]      # wildcard subject -> judge everything
