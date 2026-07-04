"""The write-time grounding score must be SURFACED on GateResult, not discarded.

Moonshot #1 (adversarial panel 5/5/5, 2026-06-20): the L4 source-entailment score
(grounding_gate.fact_grounding_score, AUROC 0.971) was computed in run_validation_gate
then thrown away after the pass/fail decision. It is now returned on
GateResult.grounding_score so the caller can persist it on the fact and condition
retrieval/answering on it — a write-time trust signal no competitor has.
"""
from __future__ import annotations

import engram.grounding_gate as gg
from engram.anti_confab_gate import run_validation_gate


def _gate(**over):
    kw = dict(proposition="Paris is the capital of France", verified_by=None, topic="geo",
              agent=None, validate="fast", source="France's capital is Paris.",
              grounding_llm=object())
    kw.update(over)
    return run_validation_gate(**kw)


def test_grounding_score_surfaced_on_pass(monkeypatch):
    monkeypatch.setenv("ENGRAM_GROUNDING_WRITE", "1")
    # the gate calls fact_grounding_score_ex (score, judge_used) since the
    # interactive-judge backend landed (2026-07-02); patch the symbol the
    # call-site resolves (late `from .grounding_gate import ...` inside
    # run_validation_gate -> module attribute lookup on gg)
    monkeypatch.setattr(gg, "fact_grounding_score_ex",
                        lambda *a, **k: (88.0, "claude"))
    res = _gate()
    assert res.grounding_score == 88.0           # captured even though it PASSED
    assert res.action == "persist"
    assert res.to_dict()["grounding_score"] == 88.0


def test_grounding_score_surfaced_on_fail(monkeypatch):
    monkeypatch.setenv("ENGRAM_GROUNDING_WRITE", "1")
    monkeypatch.setattr(gg, "fact_grounding_score_ex",
                        lambda *a, **k: (9.0, "claude"))
    res = _gate()
    assert res.grounding_score == 9.0            # low score still surfaced
    assert res.action == "downgrade"             # below threshold -> escalates


def test_none_when_grounding_off(monkeypatch):
    monkeypatch.delenv("ENGRAM_GROUNDING_WRITE", raising=False)
    res = _gate()
    assert res.grounding_score is None           # default fast path: not computed


def test_none_when_no_source(monkeypatch):
    monkeypatch.setenv("ENGRAM_GROUNDING_WRITE", "1")
    res = _gate(source=None)
    assert res.grounding_score is None           # no source -> nothing to entail against
