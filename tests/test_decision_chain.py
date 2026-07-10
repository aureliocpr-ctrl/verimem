"""Decision chain (task #15) — decisions as first-class records, TDD.

Mandate (Aurelio 2026-07-10): record the chain of DECISIONS — the choice, the
alternatives rejected, the evidence cited (fact ids), the expected outcome,
and later what actually happened — so "why did we choose X?" becomes an
answerable, cited query, and errors are explainable after the fact.

v1 storage = a dedicated isolated store (the documents.py pattern), NOT the
facts table (which has no free-form metadata column). The outcome loop obeys
the reputation-inversion guard-rail (TRUST_CORE.md): an outcome updates only
its own decision record; requires evidence; never scores the cited sources.
"""
from __future__ import annotations

import pytest

from engram.decision_chain import Decision, DecisionStore


def test_record_and_get_roundtrip(tmp_path):
    ds = DecisionStore(tmp_path / "d.db")
    did = ds.record(
        decision="Adopt the self-calibrating relevance floor",
        alternatives=["hardcode tau=0.80", "keep the fixed default"],
        evidence=["fact_aaa", "fact_bbb"],
        expected="external false_answer drops below 0.10",
        topic="decisions/read-path")
    d = ds.get(did)
    assert isinstance(d, Decision)
    assert d.decision.startswith("Adopt the self-calibrating")
    assert d.alternatives == ["hardcode tau=0.80", "keep the fixed default"]
    assert d.evidence == ["fact_aaa", "fact_bbb"]
    assert d.outcome is None and d.outcome_verified_by == []


def test_record_outcome_requires_evidence(tmp_path):
    ds = DecisionStore(tmp_path / "d.db")
    did = ds.record(decision="Ship the sim-fallback", topic="decisions/reconcile")
    with pytest.raises(ValueError):
        ds.record_outcome(did, "it worked", verified_by=[])  # guard-rail
    ok = ds.record_outcome(
        did, "mini-world stale 0.63 -> 0.10",
        verified_by=["bench:source_trust_miniworld:seed11"])
    assert ok
    d = ds.get(did)
    assert d.outcome and d.outcome_verified_by


def test_list_by_topic_newest_first(tmp_path):
    ds = DecisionStore(tmp_path / "d.db")
    a = ds.record(decision="A", topic="decisions/x", ts=100.0)
    b = ds.record(decision="B", topic="decisions/x", ts=200.0)
    ds.record(decision="C", topic="decisions/y", ts=300.0)
    got = [d.id for d in ds.list(topic="decisions/x")]
    assert got == [b, a]


def test_why_explains_with_cited_evidence(tmp_path):
    """'why did we choose X' returns the matching decision with its evidence
    ids — the chain of custody for a CHOICE, mirroring explain() for a fact."""
    ds = DecisionStore(tmp_path / "d.db")
    ds.record(decision="Use the e5 embedder as the production encoder",
              alternatives=["MiniLM-L6", "Qwen3-0.6B"],
              evidence=["fact_mrr_e5", "fact_qwen_regression"],
              expected="MRR 0.466 -> 0.710", topic="decisions/embedder")
    hits = ds.why("why did we choose the e5 embedder?")
    assert hits and "e5" in hits[0].decision.lower()
    assert "fact_mrr_e5" in hits[0].evidence


def test_persists_across_instances(tmp_path):
    ds1 = DecisionStore(tmp_path / "d.db")
    did = ds1.record(decision="Persist decisions", topic="decisions/meta")
    ds2 = DecisionStore(tmp_path / "d.db")
    assert ds2.get(did).decision == "Persist decisions"
