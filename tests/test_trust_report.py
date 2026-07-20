"""TrustReport (F3, iter 47 — mandato "affidabile per un GIUDICE").

Every answer must be able to carry its evidence dossier — the chain of custody
of the facts behind it: WHAT was used (proposition), WHERE it came from
(provenance, writer_role), HOW trusted it is (status, verified_by, grounding
score), WHEN it was true (asserted_at) vs learned (created_at), what it
REPLACED (supersession history), what it CONFLICTS with (declared disputes),
and — when there is nothing — an explicit ABSTAINED verdict instead of a guess.

This is the anti-confab / anti-hallucination / anti-sycophancy gate made ATOMIC:
one object, JSON-serializable, produced for any query. Hermetic, no LLM.
"""
from __future__ import annotations

import json
import time

from verimem.semantic import Fact, SemanticMemory
from verimem.trust_report import build_trust_report

_DAY = 86400.0


def _seed(tmp_path):
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    now = time.time()
    old = Fact(id="t-old", topic="client/rossi",
               proposition="Client Rossi's budget is 300k",
               asserted_at=now - 200 * _DAY, confidence=0.6)
    cur = Fact(id="t-cur", topic="client/rossi",
               proposition="Client Rossi's budget is 500k",
               asserted_at=now - 10 * _DAY, confidence=0.8,
               source_episodes=["conversation:mar-2026"],
               writer_role="conversational_ingest")
    rival = Fact(id="t-riv", topic="client/rossi",
                 proposition="Client Rossi's budget is 450k",
                 asserted_at=now - 5 * _DAY)
    for f in (old, cur, rival):
        sm.store(f, embed="sync")
    sm.supersede("t-old", "t-cur", reason="update")
    from verimem.contradiction import Contradiction, ContradictionStore
    ContradictionStore(sm.db_path).add(Contradiction(
        fact_a_id="t-cur", fact_b_id="t-riv",
        kind="update-conflict", similarity=0.9))
    return sm


def test_report_carries_full_chain_of_custody(tmp_path) -> None:
    sm = _seed(tmp_path)
    rep = build_trust_report(sm, "Rossi budget", k=5)
    assert rep["abstained"] is False
    used = {e["id"]: e for e in rep["facts"]}
    assert "t-cur" in used, "the live fact is in the dossier"
    cur = used["t-cur"]
    # custody chain: provenance + writer + trust status + both clocks
    assert cur["provenance"] == ["conversation:mar-2026"]
    assert cur["writer_role"] == "conversational_ingest"
    assert cur["status"] in ("model_claim", "provisional", "verified")
    assert cur["asserted_at"] is not None and cur["created_at"] is not None
    # what it REPLACED (history) and what it CONFLICTS with (declared)
    assert any("300k" in h["proposition"] for h in cur["history"]), \
        "the superseded predecessor is declared in the dossier"
    assert any("450k" in d["proposition"] for d in cur["disputes"]), \
        "the unresolved rival is DECLARED, not hidden"


def test_report_abstains_explicitly_when_no_evidence(tmp_path) -> None:
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    rep = build_trust_report(sm, "cryptozoology of Mars", k=5)
    assert rep["abstained"] is True and rep["facts"] == []
    assert rep["reason"], "an abstention carries its why"


def test_report_declares_its_trust_scope(tmp_path) -> None:
    from verimem.trust_report import TRUST_SCOPE
    sm = _seed(tmp_path)
    rep = build_trust_report(sm, "Rossi budget", k=5)
    assert rep["scope"] == TRUST_SCOPE
    # the honest boundary: corroboration is not causal truth (the causal-axis lesson)
    assert "provenance != causality" in rep["scope"]
    assert "causally true" in rep["scope"]


def test_scope_declared_even_when_abstaining(tmp_path) -> None:
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    rep = build_trust_report(sm, "anything", k=5)
    assert rep["abstained"] is True
    assert rep["scope"], "the scope boundary holds even with no facts"


def test_report_types_interventional_evidence_and_allows_causal(tmp_path) -> None:
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    sm.store(Fact(id="iv", topic="exp/ads",
                  proposition="An A/B test showed ads raise sales by 12%.",
                  asserted_at=time.time(), verified_by=["trial:ab-77"]), embed="sync")
    rep = build_trust_report(sm, "do ads raise sales", k=5)
    assert rep["facts"] and any(e["fact_type"] == "interventional"
                                for e in rep["facts"])
    assert rep["causal_answerable"] is True
    assert rep["evidence_types"]["interventional"] >= 1


def test_report_observational_only_is_not_causal_answerable(tmp_path) -> None:
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    # same retrievable proposition as the interventional case, but an OBSERVATIONAL
    # provenance (source-doc, not trial:) — the type is earned from provenance, not
    # from the words, so this stays observational and cannot settle do(X).
    sm.store(Fact(id="obs", topic="observational/ads",
                  proposition="An A/B test showed ads raise sales by 12%.",
                  asserted_at=time.time(),
                  verified_by=["source-doc:dashboard:1"]), embed="sync")
    sm.store(Fact(id="obs2", topic="observational/ads",
                  proposition="Ads and sales rose together last quarter.",
                  asserted_at=time.time(),
                  verified_by=["source-doc:report:2"]), embed="sync")
    rep = build_trust_report(sm, "do ads raise sales", k=5)
    # whatever is retrieved is observational (source-doc provenance); with no
    # interventional evidence the dossier is never causal-answerable — robust to the
    # tiny-store recall race, since empty and observational both yield False.
    assert all(e["fact_type"] == "observational" for e in rep["facts"])
    assert rep["causal_answerable"] is False        # correlation can't settle do(X)


def test_report_is_json_serializable(tmp_path) -> None:
    sm = _seed(tmp_path)
    rep = build_trust_report(sm, "Rossi budget", k=5)
    js = json.dumps(rep)          # must not raise
    assert "500k" in js


def test_min_relevance_floor_enables_llm_free_absence_abstention(tmp_path) -> None:
    """min_relevance drops sub-floor hits so a query with no relevant fact
    abstains WITHOUT an LLM (TrustMem-Bench axis 1). Default 0.0 = unchanged:
    the anisotropic bi-encoder matches any query ~0.8, so without the floor the
    dossier never abstains on an absent attribute. The floor that separates
    relevant from absent is corpus/model-dependent (hence opt-in).

    Hermetic: this exercises the FLOOR LOGIC of build_trust_report, so recall is
    stubbed to return controlled scores (the embedding separability itself is
    measured end-to-end by TrustMem-Bench, not re-derived here)."""
    from verimem import trust_report as tr
    from verimem.client import Memory
    mem = Memory(tmp_path / "f.db")
    fact = Fact(id="a", topic="u", proposition="Alex Rivera lives in Rome")
    mem.semantic.store(fact, embed="sync")
    stored = mem.semantic.get("a")

    # absent attribute scores 0.79 (anisotropic noise), relevant 0.84
    def fake_recall(query, **_kw):
        score = 0.84 if "live" in query.lower() else 0.79
        return [(stored, score)]

    orig = mem.semantic.recall
    mem.semantic.recall = fake_recall  # type: ignore[method-assign]
    try:
        # floor OFF: the absent query still yields a fact (never abstains)
        off = tr.build_trust_report(mem.semantic, "What is the blood type?")
        assert off["abstained"] is False and off["min_relevance"] == 0.0
        # floor at 0.82 (between 0.79 and 0.84): absent abstains, relevant passes
        on_abs = tr.build_trust_report(
            mem.semantic, "What is the blood type?", min_relevance=0.82)
        assert on_abs["abstained"] is True
        assert "relevance floor" in (on_abs["reason"] or "")
        on_rel = tr.build_trust_report(
            mem.semantic, "Where do they live?", min_relevance=0.82)
        assert on_rel["abstained"] is False and on_rel["n_facts"] == 1
    finally:
        mem.semantic.recall = orig  # type: ignore[method-assign]
