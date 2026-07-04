"""Tests for the HaluMem interference benchmark (stage 0 retrieval + stage 2 score)."""
from __future__ import annotations

from benchmark.halumem_interference_score import score, wilson


def test_wilson_basic_bounds() -> None:
    lo, hi = wilson(5, 10)
    assert 0.0 <= lo < 0.5 < hi <= 1.0
    # zero events → lower bound 0, upper bound below 1
    lo0, hi0 = wilson(0, 20)
    assert lo0 == 0.0 and 0.0 < hi0 < 0.3
    # empty n is defined (no crash)
    assert wilson(0, 0) == (0.0, 0.0)


def test_score_contradiction_only_headline() -> None:
    tasks = [
        {"id": 0, "label": "interference"},
        {"id": 1, "label": "interference"},
        {"id": 2, "label": "interference"},
        {"id": 3, "label": "interference"},
        {"id": 4, "label": "true"},
        {"id": 5, "label": "true"},
    ]
    verdicts = [
        {"id": 0, "relation": "CONTRADICTION"},   # caught
        {"id": 1, "relation": "CONTRADICTION"},   # caught
        {"id": 2, "relation": "UNSUPPORTED"},     # fabrication tail (not headline TPR)
        {"id": 3, "relation": "CONSISTENT"},      # missed
        {"id": 4, "relation": "CONSISTENT"},      # correct negative
        {"id": 5, "relation": "CONTRADICTION"},   # false positive
    ]
    s = score(tasks, verdicts)
    assert s["n_interference"] == 4 and s["n_control"] == 2
    # TPR contradiction-only = 2/4
    assert s["tpr_contradiction"] == 0.5
    # FPR contradiction-only = 1/2
    assert s["fpr_contradiction"] == 0.5
    # ceiling (contradiction OR unsupported) = 3/4
    assert s["detect_ceiling_contra_or_unsupported"] == 0.75
    assert s["unsupported_tail_share"] == 0.25


def test_score_missing_verdict_is_not_credited() -> None:
    """A dropped/missing verdict must count as 'not flagged', never as a catch."""
    tasks = [{"id": 0, "label": "interference"}, {"id": 1, "label": "interference"}]
    verdicts = [{"id": 0, "relation": "CONTRADICTION"}]  # id 1 missing
    s = score(tasks, verdicts)
    assert s["interference_breakdown"]["MISSING"] == 1
    assert s["tpr_contradiction"] == 0.5  # 1 of 2, missing not credited
