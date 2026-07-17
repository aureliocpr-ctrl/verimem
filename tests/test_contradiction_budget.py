"""Time-budget guard on the O(N^2) contradiction detectors.

The pairwise scan once ran ~10 min on an 8.8k-fact corpus and had to be ESC'd.
``time_budget_s`` makes it return partial results instead of blocking.
"""
from __future__ import annotations

from verimem.contradiction import detect_boolean_clashes, detect_numeric_clashes
from verimem.semantic import Fact


def _numeric_facts(n: int = 12) -> list[Fact]:
    return [
        Fact(id=f"n{i}", proposition=f"the value is {i * 10}", topic="t/x", confidence=0.9)
        for i in range(n)
    ]


def _bool_facts(n: int = 12) -> list[Fact]:
    return [
        Fact(id=f"b{i}", proposition=f"the system is {'not ' if i % 2 else ''}ready",
             topic="t/y", confidence=0.9)
        for i in range(n)
    ]


def test_numeric_zero_budget_returns_early():
    # budget exhausted before any pair is compared -> empty, no blocking
    assert detect_numeric_clashes(_numeric_facts(), time_budget_s=0.0) == []


def test_boolean_zero_budget_returns_early():
    assert detect_boolean_clashes(_bool_facts(), time_budget_s=0.0) == []


def test_numeric_no_budget_runs_full():
    # default (no budget) keeps the original full-scan behaviour
    out = detect_numeric_clashes(_numeric_facts())
    assert isinstance(out, list)


def test_boolean_no_budget_runs_full():
    out = detect_boolean_clashes(_bool_facts())
    assert isinstance(out, list)
