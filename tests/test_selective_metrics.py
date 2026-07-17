"""TDD — deployment metrics for selective prediction at DECLARED operating
points (Oxford 2603.21172 via the cortex bridge, action #1): a strong AUROC
says the scores DISCRIMINATE; it does not say the system OPERATES at the
declared risk when the operator sets λ. These metrics close that gap:

  * selective risk / coverage at a threshold;
  * AURC / E-AURC (excess over the oracle ranking — tie-conservative);
  * TCE at the λ operating point: |observed selective risk − risk the
    confidences THEMSELVES promise| (calibration), plus the SLA gap vs the
    declared target 1/(1+λ);
  * isotonic (PAV) score→P(correct) calibration, fit on dev, applied held-out.
"""
from __future__ import annotations

import pytest

from verimem.selective_metrics import (
    aurc,
    e_aurc,
    isotonic_fit,
    selective_risk_coverage,
    tce_at_lambda,
)

# (confidence, correct): 2 confident-right, 1 confident-wrong, 1 timid-right
_SMALL = [(0.9, True), (0.8, True), (0.7, False), (0.2, True)]


def test_selective_risk_coverage_at_threshold():
    r, c = selective_risk_coverage(_SMALL, threshold=0.5)
    assert c == pytest.approx(3 / 4)          # 3 of 4 answered (strict >)
    assert r == pytest.approx(1 / 3)          # 1 wrong among the 3
    r2, c2 = selective_risk_coverage(_SMALL, threshold=0.95)
    assert c2 == 0.0 and r2 is None           # nobody answers -> risk undefined


def test_aurc_hand_computed_and_tie_conservative():
    # ranking by confidence desc: T, T, F, T -> cumulative risks 0, 0, 1/3, 1/4
    assert aurc(_SMALL) == pytest.approx((0 + 0 + 1 / 3 + 1 / 4) / 4)
    # ties: the wrong one must be ranked FIRST within the tie (never flattered)
    tied = [(0.9, True), (0.9, False)]
    assert aurc(tied) == pytest.approx((1.0 + 0.5) / 2)


def test_e_aurc_zero_on_perfect_ranking_positive_otherwise():
    perfect = [(0.9, True), (0.8, True), (0.7, True), (0.2, False)]
    assert e_aurc(perfect) == pytest.approx(0.0)
    assert e_aurc(_SMALL) > 0.0


def test_tce_calibrated_scores_have_small_tce():
    """Confidences that ARE the empirical correctness rate -> observed risk
    equals what they promise -> TCE ~ 0 at an operating point they clear."""
    records = [(0.9, True)] * 9 + [(0.9, False)]        # promises 0.1 risk, delivers
    out = tce_at_lambda(records, lam=1.0)               # threshold 0.5
    assert out["coverage"] == 1.0
    assert out["observed_risk"] == pytest.approx(0.1)
    assert out["expected_risk"] == pytest.approx(0.1, abs=1e-9)
    assert out["tce"] == pytest.approx(0.0, abs=1e-9)
    assert out["sla_target_risk"] == pytest.approx(0.5)
    assert out["sla_gap"] == pytest.approx(0.1 - 0.5)   # negative = inside SLA
    assert out["sla_met"] is True


def test_tce_miscalibrated_scores_expose_the_gap():
    """Overconfident scores (0.95) that are right only half the time: the
    confidences promise 5% risk, reality is 50% -> TCE ~ 0.45, SLA violated
    at lam=3 (target 0.25)."""
    records = [(0.95, i % 2 == 0) for i in range(20)]
    out = tce_at_lambda(records, lam=3.0)               # threshold 0.75
    assert out["observed_risk"] == pytest.approx(0.5)
    assert out["tce"] == pytest.approx(0.45, abs=1e-9)
    assert out["sla_met"] is False


def test_tce_zero_coverage_is_declared_not_faked():
    records = [(0.3, True), (0.2, False)]
    out = tce_at_lambda(records, lam=9.0)               # threshold 0.9 -> nobody
    assert out["coverage"] == 0.0
    assert out["observed_risk"] is None and out["tce"] is None
    assert out["sla_met"] is None                       # inoperable, not "passed"


def test_agrees_with_benchmark_stats_aurc_on_tie_free_input():
    """Two AURC implementations live in the repo (this record-API one and
    benchmark/stats.aurc). Their tie rules differ BY DESIGN (worst-case vs
    input-order); on tie-free inputs they must agree exactly — pinned here so
    they can never silently diverge."""
    from benchmark.stats import aurc as np_aurc
    records = [(0.91, True), (0.85, False), (0.77, True), (0.60, True),
               (0.42, False), (0.13, True)]
    ours = aurc(records)
    theirs = np_aurc([c for c, _ in records], [1 if ok else 0 for _, ok in records])
    assert ours == pytest.approx(theirs, abs=1e-12)


def test_isotonic_fit_monotone_and_improves_tce():
    """PAV on dev (score, correct) pairs -> a monotone score->P map; applying
    it to badly-scaled scores must shrink TCE on a construction where raw
    scores are squeezed into a narrow band (the e5-band situation)."""
    # dev: scores squeezed in [0.70, 0.80]; low half 20% correct, high half 90%
    dev = [(0.70 + 0.001 * i, i % 10 < 2) for i in range(50)] + \
          [(0.75 + 0.001 * i, i % 10 < 9) for i in range(50)]
    cal = isotonic_fit(dev)
    # monotone
    xs = [0.65, 0.72, 0.76, 0.83]
    ps = [cal(x) for x in xs]
    assert all(b >= a - 1e-12 for a, b in zip(ps, ps[1:], strict=False))
    # held-out records from the same regime, judged at lam=1 (threshold 0.5):
    held = [(0.71, False), (0.72, False), (0.755, True), (0.76, True),
            (0.77, True), (0.78, True), (0.785, True), (0.79, False)]
    raw = tce_at_lambda(held, lam=1.0)
    calibrated = tce_at_lambda([(cal(s), ok) for s, ok in held], lam=1.0)
    assert calibrated["tce"] < raw["tce"]


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
