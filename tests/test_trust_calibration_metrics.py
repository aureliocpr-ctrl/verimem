"""R&D 2026-06-16 — calibration metrics for the trust-signal.

Pure scoring functions (no Engram state) so the calibration harness rests on
exactly-testable math: Brier score, Expected Calibration Error, reliability
table. Ground-truth outcome is binary: 1 = the fact was actually reliable.
"""
from __future__ import annotations

import pytest

from verimem.trust_calibration import (
    brier_score,
    expected_calibration_error,
    reliability_table,
)


def test_brier_perfect_is_zero() -> None:
    assert brier_score([1.0, 0.0, 1.0], [1, 0, 1]) == pytest.approx(0.0)


def test_brier_worst_is_one() -> None:
    assert brier_score([0.0, 1.0], [1, 0]) == pytest.approx(1.0)


def test_brier_uninformative_half() -> None:
    # predicting 0.5 everywhere -> MSE 0.25 regardless of outcome
    assert brier_score([0.5, 0.5, 0.5, 0.5], [1, 0, 1, 0]) == pytest.approx(0.25)


def test_brier_length_mismatch_raises() -> None:
    with pytest.raises(ValueError):
        brier_score([0.5], [1, 0])


def test_ece_perfectly_calibrated_is_zero() -> None:
    # two buckets, each prediction matches its empirical frequency exactly.
    # prob 0.0 group: 0/2 positive; prob 1.0 group: 2/2 positive.
    probs = [0.0, 0.0, 1.0, 1.0]
    outcomes = [0, 0, 1, 1]
    assert expected_calibration_error(probs, outcomes, n_bins=10) == pytest.approx(0.0)


def test_ece_miscalibrated_detected() -> None:
    # predict 0.9 but only half are positive -> gap 0.4 in that bin
    probs = [0.9, 0.9, 0.9, 0.9]
    outcomes = [1, 1, 0, 0]
    ece = expected_calibration_error(probs, outcomes, n_bins=10)
    assert ece == pytest.approx(0.4, abs=1e-9)


def test_reliability_table_buckets_and_fractions() -> None:
    probs = [0.05, 0.15, 0.95, 0.85]
    outcomes = [0, 0, 1, 1]
    table = reliability_table(probs, outcomes, n_bins=5)  # width 0.2
    # only populated bins matter, each with n + empirical positive frac
    populated = {row["bin_lo"]: row for row in table if row["n"] > 0}
    assert populated[0.0]["n"] == 2 and populated[0.0]["frac_positive"] == pytest.approx(0.0)
    assert populated[0.8]["n"] == 2 and populated[0.8]["frac_positive"] == pytest.approx(1.0)


def test_empty_inputs_safe() -> None:
    assert brier_score([], []) == pytest.approx(0.0)
    assert expected_calibration_error([], [], n_bins=5) == pytest.approx(0.0)
    assert reliability_table([], [], n_bins=5) == []
