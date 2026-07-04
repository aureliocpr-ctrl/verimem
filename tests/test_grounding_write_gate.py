"""TDD for the SEMANTIC write-path grounding level (L4) in run_validation_gate.

R10 showed the moat is on the write path: an external entailment check separates
faithful facts from confabulated inferences (AUROC 0.971 on SNLI). This wires that into
the existing (lexical) anti-confab gate as an opt-in L4 layer — when a SOURCE and a
grounding LLM are provided and ENGRAM_GROUNDING_WRITE is set, a proposition the source
does not entail is downgraded (or rejected in reject-mode). Deterministic with a stub
LLM; the default fast path (no source) is untouched.
"""
from __future__ import annotations

import types

from engram.anti_confab_gate import run_validation_gate

PROP = "Paris is the capital of France."
SRC = "France is a country in Europe; its capital city is Paris."


class StubLLM:
    def __init__(self, text: str) -> None:
        self.text = text
        self.calls = 0

    def complete(self, system, messages, *, model=None, max_tokens=None):  # noqa: ANN001
        self.calls += 1
        return types.SimpleNamespace(text=self.text)


def test_persists_when_source_entails(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setenv("ENGRAM_GROUNDING_WRITE", "1")
    llm = StubLLM("SCORE: 95")
    r = run_validation_gate(proposition=PROP, verified_by=None, topic=None, agent=None,
                            source=SRC, grounding_llm=llm)
    assert r.action == "persist"
    assert llm.calls == 1


def test_downgrades_confabulation(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setenv("ENGRAM_GROUNDING_WRITE", "1")
    llm = StubLLM("SCORE: 20")
    r = run_validation_gate(proposition=PROP, verified_by=None, topic=None, agent=None,
                            source=SRC, grounding_llm=llm)
    assert r.action == "downgrade"
    assert any(w.get("layer") == "L4-grounding" for w in r.warnings)
    assert r.warnings[-1]["grounding_score"] == 20.0


def test_rejects_confabulation_in_reject_mode(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setenv("ENGRAM_GROUNDING_WRITE", "1")
    llm = StubLLM("SCORE: 10")
    r = run_validation_gate(proposition=PROP, verified_by=None, topic=None, agent=None,
                            source=SRC, grounding_llm=llm, gate_mode="reject")
    assert r.action == "reject"


def test_off_skips_semantic_check(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.delenv("ENGRAM_GROUNDING_WRITE", raising=False)
    llm = StubLLM("SCORE: 10")  # would reject if consulted
    r = run_validation_gate(proposition=PROP, verified_by=None, topic=None, agent=None,
                            source=SRC, grounding_llm=llm)
    assert r.action == "persist"
    assert llm.calls == 0  # no LLM call when the feature is off


def test_no_source_leaves_fast_path_untouched(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setenv("ENGRAM_GROUNDING_WRITE", "1")
    llm = StubLLM("SCORE: 10")
    r = run_validation_gate(proposition=PROP, verified_by=None, topic=None, agent=None,
                            grounding_llm=llm)  # no source
    assert r.action == "persist"
    assert llm.calls == 0
