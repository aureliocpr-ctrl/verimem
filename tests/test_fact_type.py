"""Earned fact type (Vivarium P38/P49 — the causal moat): observational vs
interventional vs derived, and the routing rule that a causal claim needs
interventional evidence.
"""
from __future__ import annotations

from verimem.fact_type import (
    DERIVED,
    INTERVENTIONAL,
    OBSERVATIONAL,
    causal_answerable,
    classify_fact_type,
    evidence_type_summary,
)


def test_default_is_observational():
    assert classify_fact_type(None) == OBSERVATIONAL
    assert classify_fact_type(["source-doc:runbook:1"]) == OBSERVATIONAL
    assert classify_fact_type([], writer_role="conversational_ingest") == OBSERVATIONAL


def test_interventional_from_role_or_ref():
    assert classify_fact_type([], writer_role="experiment") == INTERVENTIONAL
    assert classify_fact_type(["trial:NCT01"]) == INTERVENTIONAL
    assert classify_fact_type(["intervention:ab-42"]) == INTERVENTIONAL
    assert classify_fact_type(["do:price=+10"]) == INTERVENTIONAL


def test_derived_from_role_or_ref():
    assert classify_fact_type([], writer_role="derived") == DERIVED
    assert classify_fact_type(["derived-from:fact-7,fact-9"]) == DERIVED
    assert classify_fact_type(["reasoning:hop-3"]) == DERIVED


def test_declared_role_wins_over_ref():
    # an explicit interventional role beats an observational-looking ref
    assert classify_fact_type(["source-doc:x"], writer_role="trial") == INTERVENTIONAL


def test_causal_answerable_needs_an_intervention():
    assert not causal_answerable([OBSERVATIONAL, OBSERVATIONAL, DERIVED])
    assert causal_answerable([OBSERVATIONAL, INTERVENTIONAL])
    assert not causal_answerable([])            # no evidence -> not answerable


def test_evidence_summary_counts():
    s = evidence_type_summary([OBSERVATIONAL, OBSERVATIONAL, INTERVENTIONAL, DERIVED])
    assert s == {OBSERVATIONAL: 2, INTERVENTIONAL: 1, DERIVED: 1}
