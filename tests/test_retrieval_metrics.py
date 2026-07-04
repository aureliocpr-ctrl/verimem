"""Cycle #113.A (2026-05-17) — retrieval metrics pure math TDD.

Per Aurelio handoff cycle 112: il bench cycle 112 baseline misurava
solo latency / Jaccard overlap (`benchmark/bench_retrieval_baseline.py`).
Per dire qualcosa sulla QUALITA' del retrieval serve ground truth.

Questo modulo locca il contratto delle metriche puri-math che il
ground-truth bench userà:

- ``precision_at_k(retrieved, relevant, k)``
- ``recall_at_k(retrieved, relevant, k)``
- ``mrr(retrieved, relevant)``  — Mean Reciprocal Rank single query
- ``wilson_ci(successes, trials, confidence=0.95)``  — confidence
  interval per A/B compare (delta retrieval variants).

Nessun I/O, nessuna dipendenza da SemanticMemory/Engram — pure
funzioni testabili in isolamento.
"""
from __future__ import annotations

import math

import pytest

from benchmark.retrieval_metrics import (
    mrr,
    precision_at_k,
    recall_at_k,
    wilson_ci,
)

# ---------------------------------------------------------------------------
# precision_at_k
# ---------------------------------------------------------------------------


class TestPrecisionAtK:
    def test_all_relevant_in_topk_returns_1(self) -> None:
        retrieved = ["a", "b", "c"]
        relevant = {"a", "b", "c"}
        assert precision_at_k(retrieved, relevant, k=3) == 1.0

    def test_no_relevant_returns_0(self) -> None:
        retrieved = ["a", "b", "c"]
        relevant = {"x", "y"}
        assert precision_at_k(retrieved, relevant, k=3) == 0.0

    def test_half_relevant_returns_half(self) -> None:
        retrieved = ["a", "x", "b", "y"]
        relevant = {"a", "b"}
        assert precision_at_k(retrieved, relevant, k=4) == 0.5

    def test_k_smaller_than_retrieved_truncates(self) -> None:
        retrieved = ["a", "b", "c", "d"]
        relevant = {"a", "c", "d"}
        # First 2 retrieved: a (relevant), b (irrelevant) -> 1/2
        assert precision_at_k(retrieved, relevant, k=2) == 0.5

    def test_k_larger_than_retrieved_uses_all(self) -> None:
        retrieved = ["a", "b"]
        relevant = {"a", "b"}
        # k=10 but only 2 retrieved: still 2/2 = 1.0 (denominator is len(retrieved))
        assert precision_at_k(retrieved, relevant, k=10) == 1.0

    def test_empty_retrieved_returns_0(self) -> None:
        assert precision_at_k([], {"a", "b"}, k=5) == 0.0

    def test_empty_relevant_returns_0(self) -> None:
        assert precision_at_k(["a", "b"], set(), k=2) == 0.0

    def test_k_zero_returns_0(self) -> None:
        assert precision_at_k(["a"], {"a"}, k=0) == 0.0

    def test_duplicate_in_retrieved_counts_once(self) -> None:
        """Defensive: a recall path returning duplicates shouldn't inflate precision."""
        retrieved = ["a", "a", "b"]
        relevant = {"a"}
        # After dedup at the prefix: top-3 has {"a", "b"} = 1 hit / 3 = 1/3
        # We accept either: count dedupped (1/2) or raw (1/3). Lock to raw (1/3)
        # for "what was actually returned" semantics.
        assert abs(precision_at_k(retrieved, relevant, k=3) - 1 / 3) < 1e-9


# ---------------------------------------------------------------------------
# recall_at_k
# ---------------------------------------------------------------------------


class TestRecallAtK:
    def test_all_relevant_found_returns_1(self) -> None:
        retrieved = ["a", "b", "c"]
        relevant = {"a", "b"}
        assert recall_at_k(retrieved, relevant, k=3) == 1.0

    def test_no_relevant_found_returns_0(self) -> None:
        retrieved = ["x", "y", "z"]
        relevant = {"a", "b"}
        assert recall_at_k(retrieved, relevant, k=3) == 0.0

    def test_half_found_returns_half(self) -> None:
        retrieved = ["a", "x", "y"]
        relevant = {"a", "b"}
        assert recall_at_k(retrieved, relevant, k=3) == 0.5

    def test_k_smaller_misses_some(self) -> None:
        retrieved = ["x", "a", "b"]
        relevant = {"a", "b"}
        # k=1: only "x" considered, 0 relevant found, recall = 0/2 = 0
        assert recall_at_k(retrieved, relevant, k=1) == 0.0

    def test_empty_relevant_returns_0(self) -> None:
        """Convention: empty ground truth -> recall = 0 (cannot recall what doesn't exist)."""
        assert recall_at_k(["a"], set(), k=1) == 0.0

    def test_empty_retrieved_returns_0(self) -> None:
        assert recall_at_k([], {"a"}, k=5) == 0.0


# ---------------------------------------------------------------------------
# MRR
# ---------------------------------------------------------------------------


class TestMRR:
    def test_first_position_returns_1(self) -> None:
        retrieved = ["a", "b", "c"]
        relevant = {"a"}
        assert mrr(retrieved, relevant) == 1.0

    def test_second_position_returns_half(self) -> None:
        retrieved = ["x", "a", "b"]
        relevant = {"a"}
        assert mrr(retrieved, relevant) == 0.5

    def test_third_position_returns_third(self) -> None:
        retrieved = ["x", "y", "a"]
        relevant = {"a"}
        assert abs(mrr(retrieved, relevant) - 1 / 3) < 1e-9

    def test_no_relevant_returns_0(self) -> None:
        retrieved = ["x", "y", "z"]
        relevant = {"a"}
        assert mrr(retrieved, relevant) == 0.0

    def test_uses_first_relevant_only(self) -> None:
        """MRR considers only the rank of the FIRST relevant item."""
        retrieved = ["x", "a", "b", "c"]
        relevant = {"a", "b", "c"}
        # First relevant at position 2 -> 1/2
        assert mrr(retrieved, relevant) == 0.5

    def test_empty_retrieved_returns_0(self) -> None:
        assert mrr([], {"a"}) == 0.0

    def test_empty_relevant_returns_0(self) -> None:
        assert mrr(["a", "b"], set()) == 0.0


# ---------------------------------------------------------------------------
# Wilson CI for A/B compare
# ---------------------------------------------------------------------------


class TestWilsonCI:
    def test_zero_trials_returns_zero_bounds(self) -> None:
        lo, hi = wilson_ci(0, 0)
        assert lo == 0.0
        assert hi == 0.0

    def test_all_successes_upper_bound_is_1(self) -> None:
        lo, hi = wilson_ci(100, 100, confidence=0.95)
        assert hi == pytest.approx(1.0, abs=1e-6)
        # Lower bound for 100/100 at 95% Wilson is ~0.9637
        assert 0.96 < lo < 0.97

    def test_zero_successes_lower_bound_is_0(self) -> None:
        lo, hi = wilson_ci(0, 100, confidence=0.95)
        assert lo == pytest.approx(0.0, abs=1e-6)
        # Upper bound for 0/100 at 95% Wilson is ~0.0370
        assert 0.03 < hi < 0.05

    def test_half_split_centered_at_0_5(self) -> None:
        lo, hi = wilson_ci(50, 100, confidence=0.95)
        # For 50/100, Wilson interval is roughly (0.402, 0.598)
        assert 0.39 < lo < 0.41
        assert 0.59 < hi < 0.61

    def test_higher_confidence_widens_interval(self) -> None:
        lo_95, hi_95 = wilson_ci(50, 100, confidence=0.95)
        lo_99, hi_99 = wilson_ci(50, 100, confidence=0.99)
        assert lo_99 < lo_95
        assert hi_99 > hi_95

    def test_more_trials_narrows_interval(self) -> None:
        lo_100, hi_100 = wilson_ci(50, 100, confidence=0.95)
        lo_1000, hi_1000 = wilson_ci(500, 1000, confidence=0.95)
        width_100 = hi_100 - lo_100
        width_1000 = hi_1000 - lo_1000
        assert width_1000 < width_100

    def test_invalid_confidence_raises(self) -> None:
        with pytest.raises(ValueError):
            wilson_ci(50, 100, confidence=1.5)
        with pytest.raises(ValueError):
            wilson_ci(50, 100, confidence=0.0)

    def test_more_successes_than_trials_raises(self) -> None:
        with pytest.raises(ValueError):
            wilson_ci(101, 100)

    def test_negative_inputs_raise(self) -> None:
        with pytest.raises(ValueError):
            wilson_ci(-1, 10)
        with pytest.raises(ValueError):
            wilson_ci(0, -5)


# ---------------------------------------------------------------------------
# Combined sanity: realistic toy query
# ---------------------------------------------------------------------------


def test_realistic_query_combined_metrics() -> None:
    """A realistic toy: ground truth has 3 facts, retrieval returns 5 (top-3
    correct, top-4-5 irrelevant)."""
    retrieved = ["f-1", "f-2", "f-3", "f-x", "f-y"]
    relevant = {"f-1", "f-2", "f-3"}
    assert precision_at_k(retrieved, relevant, k=5) == 3 / 5
    assert recall_at_k(retrieved, relevant, k=5) == 1.0
    assert mrr(retrieved, relevant) == 1.0
    # precision@3 == 1.0, recall@3 == 1.0
    assert precision_at_k(retrieved, relevant, k=3) == 1.0
    assert recall_at_k(retrieved, relevant, k=3) == 1.0
