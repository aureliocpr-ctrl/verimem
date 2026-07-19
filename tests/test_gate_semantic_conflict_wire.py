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


def test_no_llm_falls_back_to_local_nli_judge(monkeypatch):
    """Phase 1.1: with the moat ON but NO agent.llm, the gate falls back to the local
    NLI cross-encoder (llm-free) instead of skipping. The detector IS called; it must
    not crash and persists when the (stubbed) detector finds nothing."""
    monkeypatch.setenv("ENGRAM_SEMANTIC_CONFLICT", "observe")
    called = {"n": 0}
    monkeypatch.setattr(semantic_conflict, "detect_semantic_conflicts",
                        lambda *a, **k: called.__setitem__("n", called["n"] + 1) or [])
    agent = _StubAgent()
    agent.llm = None  # no subscription judge — the local NLI must take over
    res = anti_confab_gate.run_validation_gate(
        proposition="some claim", verified_by=None, topic="t",
        agent=agent, validate="full")
    assert called["n"] == 1 and res.action == "persist"


def test_llm_free_path_passes_a_local_relation_judge(monkeypatch):
    """The judge handed to the detector when there is no llm is a LocalRelationJudge."""
    from verimem.local_relation import LocalRelationJudge
    monkeypatch.setenv("ENGRAM_SEMANTIC_CONFLICT", "observe")
    seen: dict[str, object] = {}

    def _spy(new_fact, siblings, judge, *a, **k):
        seen["judge"] = judge
        return []
    monkeypatch.setattr(semantic_conflict, "detect_semantic_conflicts", _spy)
    agent = _StubAgent()
    agent.llm = None
    anti_confab_gate.run_validation_gate(
        proposition="some claim", verified_by=None, topic="t",
        agent=agent, validate="full")
    assert isinstance(seen.get("judge"), LocalRelationJudge)


def test_observe_mode_surfaces_but_does_not_quarantine(monkeypatch):
    """observe: a contradiction is LOGGED (layer L3-semantic-observe) but the write is
    ADMITTED — no downgrade, id NOT in contradicting_fact_ids — so the false-block rate
    is measurable on real tenants before enforcing (observe->enforce discipline)."""
    monkeypatch.setenv("ENGRAM_SEMANTIC_CONFLICT", "observe")
    monkeypatch.setattr(
        semantic_conflict, "detect_semantic_conflicts",
        lambda *a, **k: [CoherenceWarning(
            kind="semantic_conflict", other_fact_id="sib1", details="nli=contradiction")],
    )
    res = _gate()
    assert res.action == "persist"
    assert any(w.get("layer") == "L3-semantic-observe" for w in res.warnings)
    assert "sib1" not in res.contradicting_fact_ids


def test_enforce_escalates_even_without_llm(monkeypatch):
    """enforce + no llm: the local NLI still quarantines a contradiction (downgrade)."""
    monkeypatch.setenv("ENGRAM_SEMANTIC_CONFLICT", "1")
    monkeypatch.setattr(
        semantic_conflict, "detect_semantic_conflicts",
        lambda *a, **k: [CoherenceWarning(
            kind="semantic_conflict", other_fact_id="sib1", details="nli=contradiction")],
    )
    agent = _StubAgent()
    agent.llm = None
    res = anti_confab_gate.run_validation_gate(
        proposition="some claim", verified_by=None, topic="t",
        agent=agent, validate="full")
    assert res.action == "downgrade"
    assert any(w.get("layer") == "L3-semantic" for w in res.warnings)
    assert "sib1" in res.contradicting_fact_ids


def test_observe_same_source_evolution_labeled_supersession(monkeypatch):
    """observe: a same-source NEWER write the judge flags is labeled a supersession
    (L3-supersession-observe), NOT a contradiction — the value evolved, it is not a
    cross-source dispute. This is the deterministic fix for the measured local-NLI
    temporal over-flag."""
    monkeypatch.setenv("ENGRAM_SEMANTIC_CONFLICT", "observe")
    monkeypatch.setattr(
        semantic_conflict, "detect_semantic_conflicts",
        lambda *a, **k: [CoherenceWarning(kind="semantic_conflict", other_fact_id="sib1")])
    sib = types.SimpleNamespace(id="sib1", proposition="x", topic="t",
                                verified_by=["source-doc:acme:x"], created_at=1.0)
    agent = types.SimpleNamespace(
        llm=None, semantic=types.SimpleNamespace(all=lambda: [sib]))
    res = anti_confab_gate.run_validation_gate(
        proposition="some claim", verified_by=["source-doc:acme:x"], topic="t",
        agent=agent, validate="full")
    assert res.action == "persist"
    assert any(w.get("layer") == "L3-supersession-observe" for w in res.warnings)
    assert not any(w.get("layer") == "L3-semantic-observe" for w in res.warnings)


def test_observe_cross_source_stays_contradiction(monkeypatch):
    """observe: a DIFFERENT-source clash stays a contradiction advisory (a real dispute,
    not an evolution) — the conservative default."""
    monkeypatch.setenv("ENGRAM_SEMANTIC_CONFLICT", "observe")
    monkeypatch.setattr(
        semantic_conflict, "detect_semantic_conflicts",
        lambda *a, **k: [CoherenceWarning(kind="semantic_conflict", other_fact_id="sib1")])
    sib = types.SimpleNamespace(id="sib1", proposition="x", topic="t",
                                verified_by=["source-doc:globex:x"], created_at=1.0)
    agent = types.SimpleNamespace(
        llm=None, semantic=types.SimpleNamespace(all=lambda: [sib]))
    res = anti_confab_gate.run_validation_gate(
        proposition="some claim", verified_by=["source-doc:acme:x"], topic="t",
        agent=agent, validate="full")
    assert any(w.get("layer") == "L3-semantic-observe" for w in res.warnings)
    assert not any(w.get("layer") == "L3-supersession-observe" for w in res.warnings)


def _evo_agent():
    sib = types.SimpleNamespace(id="sib1", proposition="x", topic="t",
                                verified_by=["source-doc:acme:x"], created_at=1.0)
    return types.SimpleNamespace(
        llm=None, semantic=types.SimpleNamespace(all=lambda: [sib]))


def _stub_conflict(monkeypatch):
    monkeypatch.setattr(
        semantic_conflict, "detect_semantic_conflicts",
        lambda *a, **k: [CoherenceWarning(kind="semantic_conflict", other_fact_id="sib1")])


def test_enforce_evolution_with_flag_populates_supersede_ids(monkeypatch):
    """enforce + ENGRAM_SUPERSEDE_SAME_SOURCE: a same-source evolution routes the OLD sib
    to supersede_fact_ids (retire old) and ADMITS the new — not quarantine."""
    monkeypatch.setenv("ENGRAM_SEMANTIC_CONFLICT", "1")
    monkeypatch.setenv("ENGRAM_SUPERSEDE_SAME_SOURCE", "enforce")
    _stub_conflict(monkeypatch)
    res = anti_confab_gate.run_validation_gate(
        proposition="some claim", verified_by=["source-doc:acme:x"], topic="t",
        agent=_evo_agent(), validate="full")
    assert res.action == "persist"                        # new admitted
    assert res.supersede_fact_ids == ["sib1"]             # old retired
    assert "sib1" not in res.contradicting_fact_ids


def test_enforce_evolution_without_flag_quarantines_as_before(monkeypatch):
    """enforce, supersede flag OFF (default): an evolution falls back to the current
    contradiction behavior (quarantine new), no supersede_fact_ids — safe default."""
    monkeypatch.setenv("ENGRAM_SEMANTIC_CONFLICT", "1")
    monkeypatch.delenv("ENGRAM_SUPERSEDE_SAME_SOURCE", raising=False)
    _stub_conflict(monkeypatch)
    res = anti_confab_gate.run_validation_gate(
        proposition="some claim", verified_by=["source-doc:acme:x"], topic="t",
        agent=_evo_agent(), validate="full")
    assert res.action == "downgrade"                      # new quarantined (unchanged)
    assert res.supersede_fact_ids == []
    assert "sib1" in res.contradicting_fact_ids


def test_enforce_cross_source_never_supersedes(monkeypatch):
    """enforce + supersede flag ON: a CROSS-source clash is NOT an evolution → stays a
    contradiction (quarantine new), never a supersede — the griefing guard."""
    monkeypatch.setenv("ENGRAM_SEMANTIC_CONFLICT", "1")
    monkeypatch.setenv("ENGRAM_SUPERSEDE_SAME_SOURCE", "enforce")
    _stub_conflict(monkeypatch)
    sib = types.SimpleNamespace(id="sib1", proposition="x", topic="t",
                                verified_by=["source-doc:globex:x"], created_at=1.0)
    agent = types.SimpleNamespace(
        llm=None, semantic=types.SimpleNamespace(all=lambda: [sib]))
    res = anti_confab_gate.run_validation_gate(
        proposition="some claim", verified_by=["source-doc:acme:x"], topic="t",
        agent=agent, validate="full")
    assert res.action == "downgrade"
    assert res.supersede_fact_ids == []
    assert "sib1" in res.contradicting_fact_ids


def test_llm_free_moat_fires_end_to_end(monkeypatch):
    """Adversarial 'claim→reality' proof: with NO agent.llm, the REAL
    detect_semantic_conflicts + REAL cosine pre-filter + an injected stub-classifier
    LocalRelationJudge produce the warning through the gate — the moat is a live path,
    NOT dead wiring. Only the two heavy models (sentence embedder, NLI weights) are
    faked; the wiring, the cosine gate and the decision logic are the real code."""
    import numpy as np

    from verimem import embedding, local_relation
    from verimem.local_relation import LocalRelationJudge

    monkeypatch.setenv("ENGRAM_SEMANTIC_CONFLICT", "observe")
    # fake embedder: identical vector → cosine 1.0 ≥ min_cosine, so the candidate
    # actually reaches the judge (we are proving the wire, not the embedder).
    monkeypatch.setattr(embedding, "encode", lambda text: np.array([1.0, 0.0, 0.0]))

    def _contra_classifier(pairs):  # no transformers — a contradiction verdict
        return [{"contradiction": 0.9, "entailment": 0.0, "neutral": 0.1}
                for _ in pairs]
    local_relation.set_local_relation_judge(
        LocalRelationJudge(classifier=_contra_classifier))
    try:
        agent = _StubAgent()
        agent.llm = None
        res = anti_confab_gate.run_validation_gate(
            proposition="the server is up", verified_by=None, topic="t",
            agent=agent, validate="full")
    finally:
        local_relation.set_local_relation_judge(None)  # reset process singleton
    assert res.action == "persist"  # observe never quarantines
    assert any(w.get("layer") == "L3-semantic-observe" for w in res.warnings)
