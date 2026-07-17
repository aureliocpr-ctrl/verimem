"""Characterization tests for L1.21 quality-superlative detector (F2 gap).

The detector backstops the sycophancy/overclaim vector ("flawless",
"bug-free", "the perfect deploy") that the embedding L1.20 lets slip under a
flattery prefix. It shipped exercised only by the red-team corpus; F2 pins its
behavior with unit tests so a refactor can't silently weaken a trust defense.
"""
from __future__ import annotations

import pytest

from verimem.l1_quality_detector import detect_unsupported_quality_claim as det


def _fires(prop, verified_by=None):
    return det(proposition=prop, verified_by=verified_by) is not None


@pytest.mark.parametrize("prop", [
    "The pipeline is flawless and ready.",
    "This module is bug-free.",
    "Our deploy is bulletproof.",
    "The build is rock-solid now.",
    "Shipped with zero bugs.",
    "No bugs remain in the parser.",
    "The service is 100% reliable.",
    "This path never fails.",
])
def test_strong_overclaims_fire(prop):
    assert _fires(prop), f"strong overclaim should warn: {prop!r}"


@pytest.mark.parametrize("prop", [
    "This is the perfect deployment.",
    "We built the perfect release pipeline.",
    "The codebase is perfect.",
])
def test_perfect_qualifying_a_system_noun_fires(prop):
    assert _fires(prop)


@pytest.mark.parametrize("prop", [
    "It is the perfect time to migrate.",
    "She made a perfect cup of coffee.",
    "The code compiles and runs.",
    "We reduced latency by 20%.",
    "",
])
def test_benign_or_ambiguous_does_not_fire(prop):
    assert not _fires(prop)


def test_evidence_disarms_the_warning():
    # a runtime/test ref clears it, like every L1 detector
    assert not _fires("The pipeline is flawless.",
                      verified_by=["pytest:test_pipeline passed"])
    assert not _fires("Zero bugs.", verified_by=["bench:latency_p95"])


def test_unsupported_stays_warned_without_outcome_token():
    # a bare "pytest:" ref with no pass/green outcome is NOT evidence
    assert _fires("The system is bulletproof.",
                  verified_by=["note:looks good to me"])


def test_warning_carries_matched_text_and_advice():
    w = det(proposition="It is bug-free.", verified_by=None)
    assert w is not None
    assert "bug" in w.matched_text.lower()
    assert "evidence" in w.advice.lower() or "goal" in w.advice.lower()
