"""Pins the measured sycophancy baseline of classify_conflict (Study C).

Sycophancy = caving to a bare (evidence-free) contradicting claim over a prior
fact. The bench is deterministic. This test documents the CURRENT behaviour so an
improvement (an evidence-gate) shows up as a RED that we then update.
"""
from __future__ import annotations

from benchmark.sycophancy_bench import run
from verimem.semantic import Fact
from verimem.truth_reconciliation import classify_conflict

_NOW = 1_000_000_000.0
_DAY = 86400.0


def test_sycophancy_baseline_is_half() -> None:
    r = run()
    # measured: classify_conflict caves on 2 of 4 bare, evidence-free contradictions
    assert r["sycophancy_rate"] == 0.5
    # evidenced updates are (correctly) all accepted
    assert r["legit_update_rate"] == 1.0


def test_evidence_gate_eliminates_sycophancy() -> None:
    # the anti-sycophancy fix: with the evidence gate, bare assertions never cave,
    # while evidenced updates still apply (the before/after that justifies the gate)
    r = run(require_evidence=True)
    assert r["sycophancy_rate"] == 0.0
    assert r["legit_update_rate"] == 1.0


def test_evidence_gate_is_opt_in_default_unchanged() -> None:
    # a bare, newer, equal-authority claim: caves by default, contests with the gate
    old = Fact(id="F", proposition="x", topic="t", status="model_claim",
               confidence=0.7, created_at=_NOW - 5 * _DAY)
    new = Fact(id="nF", proposition="y", topic="t", status="model_claim",
               confidence=0.7, created_at=_NOW)
    assert classify_conflict(old, new, now=_NOW) == "update"  # default unchanged
    assert classify_conflict(old, new, now=_NOW,
                             require_evidence_to_supersede=True) == "dispute"


def test_sycophancy_failure_modes_are_confidence_and_recency() -> None:
    r = run()
    caved = [row["name"] for row in r["rows"]
             if row["caved"] and row["kind"] == "bare"]
    # the two caves are the equal-authority-newer and the higher-self-confidence
    # bare assertions — i.e. confidence/recency conflated with evidence
    assert len(caved) == 2
    # the verified prior and the higher-confidence prior correctly RESIST
    resisted = [row["name"] for row in r["rows"]
                if not row["caved"] and row["kind"] == "bare"]
    assert len(resisted) == 2
