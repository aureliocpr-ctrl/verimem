"""Cycle #113.A + #113.C — compare_retrieval_variants tests."""
from __future__ import annotations

import pytest

from benchmark.compare_retrieval_variants import (
    _binarize,
    _ci_non_overlap,
    _mean_with_normal_ci,
    compare,
)

# ---------------------------------------------------------------------------
# _binarize
# ---------------------------------------------------------------------------


def test_binarize_counts_metric_above_threshold() -> None:
    per_query = [
        {"mrr": 1.0}, {"mrr": 0.5}, {"mrr": 0.0}, {"mrr": 1.0},
    ]
    s, n = _binarize(per_query, metric="mrr", threshold=1.0)
    assert (s, n) == (2, 4)


def test_binarize_geq_vs_gt() -> None:
    per_query = [{"x": 0.5}, {"x": 1.0}]
    assert _binarize(per_query, metric="x", threshold=1.0, geq=True) == (1, 2)
    assert _binarize(per_query, metric="x", threshold=1.0, geq=False) == (0, 2)


def test_binarize_missing_metric_defaults_to_zero() -> None:
    per_query = [{"other": 1.0}]
    s, n = _binarize(per_query, metric="mrr", threshold=0.5)
    assert (s, n) == (0, 1)


# ---------------------------------------------------------------------------
# _mean_with_normal_ci
# ---------------------------------------------------------------------------


def test_mean_with_normal_ci_basic() -> None:
    out = _mean_with_normal_ci([0.5] * 100)
    assert out["mean"] == 0.5
    assert out["ci_lo"] == 0.5
    assert out["ci_hi"] == 0.5  # zero variance
    assert out["n"] == 100


def test_mean_with_normal_ci_empty() -> None:
    out = _mean_with_normal_ci([])
    assert out == {"mean": 0.0, "ci_lo": 0.0, "ci_hi": 0.0, "n": 0}


def test_mean_with_normal_ci_clips_to_unit_interval() -> None:
    out = _mean_with_normal_ci([1.0] * 5)
    assert 0.0 <= out["ci_lo"] <= 1.0
    assert 0.0 <= out["ci_hi"] <= 1.0


# ---------------------------------------------------------------------------
# _ci_non_overlap
# ---------------------------------------------------------------------------


def test_ci_non_overlap_disjoint() -> None:
    assert _ci_non_overlap(0.0, 0.1, 0.5, 0.6) is True
    assert _ci_non_overlap(0.5, 0.6, 0.0, 0.1) is True


def test_ci_overlap_returns_false() -> None:
    assert _ci_non_overlap(0.0, 0.5, 0.4, 0.7) is False  # touch
    assert _ci_non_overlap(0.0, 0.5, 0.5, 0.7) is False  # exact touch
    assert _ci_non_overlap(0.0, 1.0, 0.3, 0.4) is False  # contained


# ---------------------------------------------------------------------------
# compare
# ---------------------------------------------------------------------------


def test_compare_length_mismatch_raises() -> None:
    with pytest.raises(ValueError, match="length mismatch"):
        compare(
            [{"mrr": 1.0, "recall_at_k": 1.0, "precision_at_k": 1.0}],
            [],
        )


def test_compare_identical_inputs_zero_delta() -> None:
    pq = [
        {"mrr": 1.0, "recall_at_k": 1.0, "precision_at_k": 0.2},
        {"mrr": 0.5, "recall_at_k": 0.5, "precision_at_k": 0.1},
        {"mrr": 0.0, "recall_at_k": 0.0, "precision_at_k": 0.0},
    ] * 20  # n=60, big enough for CI math
    result = compare(pq, pq)
    assert result["n_queries"] == 60
    for m in result["metrics"].values():
        if "delta" in m:
            assert m["delta"] == 0.0
        elif "delta_mean" in m:
            assert m["delta_mean"] == 0.0


def test_compare_clearly_better_experimental() -> None:
    """Synthesise a scenario where experimental dominates 100-0 on hit_at_1.
    CI intervals should not overlap, intervals_non_overlap=True."""
    n = 200
    baseline = [{"mrr": 0.0, "recall_at_k": 0.0, "precision_at_k": 0.0}] * n
    experimental = [{"mrr": 1.0, "recall_at_k": 1.0, "precision_at_k": 1.0}] * n
    result = compare(baseline, experimental)
    # On hit_at_1, baseline rate=0/200, experimental rate=200/200 — clearly disjoint
    hit = result["metrics"]["hit_at_1"]
    assert hit["intervals_non_overlap"] is True
    assert hit["delta"] == pytest.approx(1.0, abs=1e-6)
