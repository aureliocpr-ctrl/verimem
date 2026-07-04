"""Guards for the pure helpers of the real-gate provenance harness (roc_auc, wilson).
The end-to-end behavior is validated by running the harness (serial claude -p); these
keep the separation/CI math from rotting. Hermetic, no LLM."""
from __future__ import annotations

from benchmark.grounding_conditioned_qa_real import roc_auc, wilson


def test_roc_auc_perfect_separation():
    # every true score above every distractor -> AUROC 1.0
    assert roc_auc([90.0, 80.0, 95.0], [10.0, 0.0, 20.0]) == 1.0


def test_roc_auc_inverted_is_zero():
    assert roc_auc([0.0, 5.0], [90.0, 95.0]) == 0.0


def test_roc_auc_ties_count_half():
    # one tie (50 vs 50), one clear win (50 vs 10) -> (1 + 0.5) / 2 = 0.75
    assert roc_auc([50.0, 50.0], [50.0, 10.0]) == 0.75


def test_roc_auc_empty_is_none():
    assert roc_auc([], [1.0]) is None
    assert roc_auc([1.0], []) is None


def test_wilson_interval_bounds():
    lo, hi = wilson(0, 12)  # 0 hallucinations out of 12
    assert lo == 0.0 and 0.0 < hi < 0.3  # upper bound is non-trivial, not 0
    lo2, hi2 = wilson(6, 12)
    assert lo2 < 0.5 < hi2  # symmetric around 0.5
