"""Tie-correctness of the benchmark AUROC (Mann-Whitney with average ranks).

The bug that motivated this: the original `_auroc` ranked by insertion order, so a
signal with many tied scores (e.g. a judge emitting lots of '100') got a badly biased
AUC — it produced AUROC 0.236 with sound-mean (98.2) > patho-mean (87.5), which is
impossible for a correct AUROC. These tests pin the tie-corrected behaviour.
"""
from __future__ import annotations

import math

from benchmark.calibration_bench import _auroc


def test_perfect_separation() -> None:
    assert _auroc([1, 2, 3, 4], [0, 0, 1, 1]) == 1.0


def test_perfect_inversion() -> None:
    assert _auroc([4, 3, 2, 1], [0, 0, 1, 1]) == 0.0


def test_all_tied_is_half() -> None:
    # every score identical -> no ranking information -> AUROC must be exactly 0.5
    # (the OLD insertion-order implementation returned 0.0 here — the bug).
    assert _auroc([5, 5, 5, 5], [1, 1, 0, 0]) == 0.5


def test_partial_ties_consistent_with_mean() -> None:
    # sound scores stochastically dominate -> AUROC must be > 0.5 (the property the
    # span result violated under the buggy implementation).
    auc = _auroc([100, 100, 100, 90, 100, 80], [1, 1, 1, 0, 0, 0])
    assert auc > 0.5


def test_degenerate_single_class_is_nan() -> None:
    assert math.isnan(_auroc([1, 2, 3], [1, 1, 1]))
