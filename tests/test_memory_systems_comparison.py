"""TDD for the comparative belief-integrity benchmark (Engram TMS vs mem0/Zep-style)."""
from __future__ import annotations

from benchmark.memory_systems_comparison import run, run_once


def test_engram_beats_baselines_on_jbi_without_losing_recall() -> None:
    r = run_once(n_foundations=40, n_derived=100, seed=0)
    # cascade strictly helps belief-integrity: engram >= zep-style >= mem0-style
    assert r["engram_jbi"] >= r["edge_jbi"] >= r["naive_jbi"]
    # and engram does NOT win by over-retracting valid facts
    assert r["engram_recall"] == 1.0
    # engram serves no falsehood (propagate retracts every derived-of-invalid)
    assert r["engram_jbi"] == 1.0


def test_aggregate_reports_gain_and_recall_guard() -> None:
    res = run(n_foundations=30, n_derived=70, seeds=8)
    assert res["jbi_gain_vs_zep_style"] > 0.0          # cascade adds measurable integrity
    assert res["engram_preserves_valid_recall"] is True
    assert res["engram_tms_this_work"]["jbi"]["mean"] >= res["edge_invalidation_zep_style"]["jbi"]["mean"]


def test_no_cascade_no_gap() -> None:
    # honesty guard: with ZERO derived facts (no derivation chains, like today's real corpus),
    # cascade has nothing to act on -> engram and zep-style are identical.
    r = run_once(n_foundations=100, n_derived=0, seed=3)
    assert r["engram_jbi"] == r["edge_jbi"]
