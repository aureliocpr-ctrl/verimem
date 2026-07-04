"""Pure-metric tests for the local-NLI interference bench (roc_auc / sweep).
No model, no dataset — pins the scoring math the empirical run rides on."""
from __future__ import annotations

from benchmark.interference_local_nli import roc_auc, sweep_tpr_fpr


def test_roc_auc_perfect_separation() -> None:
    assert roc_auc([1, 1, 0, 0], [0.9, 0.8, 0.2, 0.1]) == 1.0


def test_roc_auc_all_ties_is_half() -> None:
    assert roc_auc([1, 0, 1, 0], [0.5, 0.5, 0.5, 0.5]) == 0.5


def test_roc_auc_inverted_is_zero() -> None:
    assert roc_auc([1, 1, 0, 0], [0.1, 0.2, 0.8, 0.9]) == 0.0


def test_roc_auc_needs_both_classes() -> None:
    assert roc_auc([1, 1, 1], [0.9, 0.8, 0.7]) is None


def test_sweep_endpoints_and_midpoint() -> None:
    labels = [1, 1, 0, 0]
    scores = [0.9, 0.6, 0.4, 0.1]
    s = sweep_tpr_fpr(labels, scores, [0.0, 0.5, 1.01])
    assert s[0.0]["tpr"] == 1.0 and s[0.0]["fpr"] == 1.0     # threshold 0 flags all
    assert s[1.01]["tpr"] == 0.0 and s[1.01]["fpr"] == 0.0   # above max flags none
    # both positives (0.9, 0.6) >= 0.5 and both negatives (0.4, 0.1) < 0.5 => perfect
    assert s[0.5]["tpr"] == 1.0 and s[0.5]["fpr"] == 0.0
