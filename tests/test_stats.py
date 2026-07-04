"""TDD for benchmark/stats.py — the Phase-0 statistics primitives."""
from __future__ import annotations

import math

from benchmark.stats import aurc, auroc, bootstrap_ci, delong_test, ece


def test_auroc_perfect() -> None:
    assert auroc([1, 2, 3, 4], [0, 0, 1, 1]) == 1.0


def test_auroc_inverted() -> None:
    assert auroc([4, 3, 2, 1], [0, 0, 1, 1]) == 0.0


def test_auroc_all_tied_is_half() -> None:
    assert auroc([5, 5, 5, 5], [1, 1, 0, 0]) == 0.5


def test_auroc_single_class_nan() -> None:
    assert math.isnan(auroc([1, 2, 3], [1, 1, 1]))


def test_aurc_known_value() -> None:
    # order by score desc: correct=[1,1,0]; risk=[0,0,1/3]; mean≈0.111
    assert abs(aurc([3, 2, 1], [1, 1, 0]) - (1 / 3) / 3) < 1e-9


def test_aurc_perfect_is_zero_until_tail() -> None:
    # all-correct accepted first -> zero risk throughout
    assert aurc([3, 2, 1], [1, 1, 1]) == 0.0


def test_bootstrap_ci_brackets_point() -> None:
    scores = [0.9, 0.8, 0.7, 0.6, 0.2, 0.1, 0.15, 0.05]
    labels = [1, 1, 1, 1, 0, 0, 0, 0]
    point, lo, hi = bootstrap_ci(scores, labels, b=1000, seed=0)
    assert point == 1.0
    assert 0.0 <= lo <= point <= hi <= 1.0


def test_bootstrap_ci_deterministic() -> None:
    scores = [0.9, 0.6, 0.7, 0.2, 0.4, 0.1]
    labels = [1, 1, 0, 0, 1, 0]
    a = bootstrap_ci(scores, labels, b=500, seed=42)
    b = bootstrap_ci(scores, labels, b=500, seed=42)
    assert a == b  # same seed -> identical CI


def test_ece_perfectly_calibrated_is_zero() -> None:
    # prob exactly equals outcome in each bin -> 0 calibration error
    assert ece([1.0, 1.0, 0.0, 0.0], [1, 1, 0, 0]) == 0.0


def test_ece_overconfident_is_high() -> None:
    # claims 100% but half are wrong -> ECE ~0.5
    assert ece([1.0, 1.0, 1.0, 1.0], [1, 0, 1, 0]) > 0.4


def test_delong_identical_predictors_p_one() -> None:
    scores = [0.9, 0.8, 0.2, 0.1, 0.6, 0.3]
    labels = [1, 1, 0, 0, 1, 0]
    out = delong_test(scores, scores, labels)
    assert out["auc_a"] == out["auc_b"]
    assert out["p"] == 1.0


def test_delong_clear_difference_is_significant() -> None:
    labels = [1] * 20 + [0] * 20
    a = [1.0] * 20 + [0.0] * 20            # perfect separator, AUC=1
    b = [float(i % 2) for i in range(40)]   # uninformative, AUC≈0.5
    out = delong_test(a, b, labels)
    assert out["auc_a"] > out["auc_b"]
    assert out["p"] < 0.05
