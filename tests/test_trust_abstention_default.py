"""Abstention on the trust_report path — honesty + an opt-in sufficiency judge.

Measured 2026-07-21 on the 20-pair confab corpus (probe_trust_abstention):
  - bi-encoder cosine: IMP max 0.848 vs ANS min 0.830 — NOT separable; the
    min_relevance floor can never fire on absent attributes. Dead road.
  - reranker CE logit: 4/10 impossible fall below 0 vs answerable >= 8.19 —
    a floor would catch those 4 with zero answerable lost, BUT 6/10 impossible
    still score high (bridge-temporal 8.97): relevance != sufficiency.

DELIBERATELY NOT DONE HERE: flipping ce_gate ON by default across every SDK
recall. 10 synthetic cases cannot justify a load-bearing default flip that
touches all deployments — that is the exact mistake the telemetry-routing
default taught (caught only by an external-corpus bench). The env switch
ENGRAM_MIN_RELEVANCE=auto already makes CE abstention reachable; making it the
default needs a TruthfulQA/HaluEval-scale measurement, proposed not smuggled.

Cures pinned here (observe-first, no global default flip):
  1. no silent fail-open (kimi F3a): the report SAYS whether the gate ran —
     'ran' | 'unavailable' | 'error' | 'off'. The old code swallowed scorer
     faults and served unfiltered hits with the same receipt as a ran gate.
  2. opt-in ``llm=`` sufficiency judge for the residual class — relevance is
     not sufficiency, and only a question-aware check closes it.
"""
from __future__ import annotations

import pytest

import verimem.trust_report as tr
from verimem.trust_report import build_trust_report


class _FakeFact:
    def __init__(self, text: str) -> None:
        self.id = "f-" + text[:8]
        self.proposition = text
        self.topic = "t/x"
        self.status = "model_claim"
        self.confidence = 0.8
        self.created_at = 1000.0
        self.asserted_at = 1000.0
        self.source_episodes = []
        self.verified_by = []
        self.grounding_score = None
        self.fact_type = "observational"


class _FakeSM:
    """Semantic-memory stub: recall returns (fact, cosine) pairs like the real
    one; the cosine is deliberately HIGH everywhere (the measured anisotropy)."""

    def __init__(self, texts: list[str]) -> None:
        self._hits = [(_FakeFact(t), 0.84) for t in texts]

    def recall(self, query, k=5, **kw):  # noqa: ANN001
        return self._hits[:k]


class _Resp:
    def __init__(self, text: str) -> None:
        self.text = text


class ScoreLLM:
    def __init__(self, text: str) -> None:
        self._text = text
        self.calls = 0

    def complete(self, system, messages, **kw):  # noqa: ANN001
        self.calls += 1
        return _Resp(self._text)


@pytest.fixture
def sm() -> _FakeSM:
    return _FakeSM(["The office in Milan has 40 desks."])


def _patch_reranker(monkeypatch, scorer):
    import verimem.semantic as semantic
    monkeypatch.setattr(semantic, "_load_reranker", lambda: scorer)


# ------------------------------------------- ce_gate when explicitly requested

def test_gate_on_drops_offtopic_and_abstains(sm, monkeypatch):
    """The measured shape: cosine 0.84 (anisotropy) but CE logit negative —
    with ce_gate requested the report abstains."""
    _patch_reranker(monkeypatch, lambda pairs: [-5.6 for _ in pairs])
    rep = build_trust_report(sm, "Who does Elena report to?", ce_gate=True)
    assert rep["abstained"] is True
    assert rep["n_facts"] == 0
    assert rep["verify"]["ce_gate"] == "ran"


def test_gate_on_keeps_relevant_facts(sm, monkeypatch):
    _patch_reranker(monkeypatch, lambda pairs: [10.9 for _ in pairs])
    rep = build_trust_report(sm, "How many desks does the Milan office have?",
                             ce_gate=True)
    assert rep["abstained"] is False
    assert rep["n_facts"] == 1
    assert rep["verify"]["ce_gate"] == "ran"


def test_gate_off_is_the_default_and_explicit_in_the_receipt(sm):
    """No global default flip: the SDK still routes ce_gate via the env
    switch, so the low-level default stays off — but the receipt SAYS so."""
    rep = build_trust_report(sm, "anything")
    assert rep["verify"]["ce_gate"] == "off"
    assert rep["n_facts"] == 1          # unchanged default behaviour


# --------------------------------------------------------- F3a: no silent fail

def test_reranker_unavailable_is_declared_not_silent(sm, monkeypatch):
    _patch_reranker(monkeypatch, None)
    rep = build_trust_report(sm, "anything", ce_gate=True)
    assert rep["verify"]["ce_gate"] == "unavailable"
    assert rep["n_facts"] == 1          # degraded, but SAID


def test_scorer_error_is_declared_not_silent(sm, monkeypatch):
    def _boom(pairs):  # noqa: ANN001
        raise RuntimeError("scorer exploded")

    _patch_reranker(monkeypatch, _boom)
    rep = build_trust_report(sm, "anything", ce_gate=True)
    assert rep["verify"]["ce_gate"] == "error"
    assert rep["n_facts"] == 1


# ------------------------------------------------- opt-in sufficiency (llm=)

def test_sufficiency_judge_abstains_on_relevant_but_insufficient(sm, monkeypatch):
    """The residual class: the reranker calls the fact relevant (8.97
    measured) but it does not CONTAIN the answer. The opt-in judge closes it."""
    _patch_reranker(monkeypatch, lambda pairs: [8.97 for _ in pairs])
    llm = ScoreLLM("Score: 10")
    rep = build_trust_report(sm, "On what date did the migration finish?",
                             llm=llm)
    assert llm.calls == 1
    assert rep["abstained"] is True
    assert rep["verify"]["sufficiency"] == "ran"
    assert rep["reason"] and "sufficien" in rep["reason"]


def test_sufficiency_judge_keeps_sufficient_facts(sm, monkeypatch):
    _patch_reranker(monkeypatch, lambda pairs: [10.9 for _ in pairs])
    llm = ScoreLLM("Score: 95")
    rep = build_trust_report(sm, "How many desks does the Milan office have?",
                             llm=llm)
    assert rep["abstained"] is False
    assert rep["n_facts"] == 1
    assert rep["verify"]["sufficiency"] == "ran"


def test_no_llm_means_sufficiency_off(sm, monkeypatch):
    _patch_reranker(monkeypatch, lambda pairs: [10.9 for _ in pairs])
    rep = build_trust_report(sm, "anything")
    assert rep["verify"]["sufficiency"] == "off"


def test_unreadable_sufficiency_verdict_declared_and_facts_kept(sm, monkeypatch):
    """A judge flake must not destroy the dossier: facts stay, receipt says
    the sufficiency check could not be read."""
    _patch_reranker(monkeypatch, lambda pairs: [10.9 for _ in pairs])
    llm = ScoreLLM("no digits in this verdict")
    rep = build_trust_report(sm, "anything", llm=llm)
    assert rep["abstained"] is False
    assert rep["verify"]["sufficiency"] == "unreadable"


def test_sdk_explain_forwards_llm(tmp_path, monkeypatch):
    """Memory.explain must expose the same opt-in sufficiency judge."""
    from verimem.client import Memory
    m = Memory(path=tmp_path / "m.db")
    m.add("The office in Milan has 40 desks.", topic="t/x",
          source="The office in Milan has 40 desks.", verified_by=["sd:1"])
    _patch_reranker(monkeypatch, lambda pairs: [8.97 for _ in pairs])
    llm = ScoreLLM("Score: 10")
    rep = m.explain("On what date did the migration finish?", llm=llm)
    assert llm.calls == 1
    assert rep["abstained"] is True
    assert tr is not None
