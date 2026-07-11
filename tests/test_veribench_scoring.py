"""VeriBench scoring core (#11 v0) — NET = (correct − λ·wrong)/n, λ-sweep, coverage.

The load-bearing test is `test_lambda_sweep_reveals_what_symmetric_hides`: an
executable proof of the seed thesis (VERIBENCH_DESIGN_INPUTS.md §1) that symmetric
(λ=1) scoring makes a trust memory's core property invisible.
"""
from __future__ import annotations

import pytest

from benchmark.veribench.scoring import (
    DEFAULT_LAMBDAS,
    Outcome,
    counts,
    coverage,
    crossover_lambda,
    net_score,
    scorecard,
)

C, W, A = Outcome.CORRECT, Outcome.WRONG, Outcome.ABSTAIN


def test_net_score_symmetric_and_asymmetric():
    o = [C] * 8 + [W] * 2
    assert net_score(o, 1.0) == pytest.approx(0.6)     # (8 − 1·2)/10
    assert net_score(o, 5.0) == pytest.approx(-0.2)    # (8 − 5·2)/10
    assert net_score([], 2.0) == 0.0                   # empty → 0, no crash


def test_coverage_excludes_abstention():
    o = [C] * 6 + [W] * 1 + [A] * 3
    assert coverage(o) == pytest.approx(0.7)           # 7 answered / 10
    assert counts(o) == {"n": 10, "correct": 6, "wrong": 1, "abstain": 3}


def test_abstention_counts_in_denominator_not_as_wrong():
    # silence is a choice, not a miss: it drags coverage but never nets negative
    honest = [C] * 5 + [A] * 5
    assert net_score(honest, 10.0) == pytest.approx(0.5)   # no wrong → λ-immune
    assert coverage(honest) == pytest.approx(0.5)


def test_crossover_lambda():
    assert crossover_lambda([C] * 6 + [W] * 2) == pytest.approx(3.0)  # 6/2
    assert crossover_lambda([C] * 5 + [A] * 5) is None               # never crosses


def test_lambda_sweep_reveals_what_symmetric_hides():
    """THE point of VeriBench. Two systems with the SAME symmetric (λ=1) net —
    a fabricator that answers everything and an honest one that abstains when
    unsure. λ=1 cannot tell them apart; the λ-sweep does."""
    fabricator = [C] * 8 + [W] * 2                 # coverage 1.0, 2 wrong
    honest = [C] * 6 + [A] * 4                      # coverage 0.6, 0 wrong

    # invisible under symmetric scoring — identical
    assert net_score(fabricator, 1.0) == net_score(honest, 1.0) == pytest.approx(0.6)
    # revealed as soon as a wrong answer costs more than silence
    assert net_score(fabricator, 5.0) < 0 < net_score(honest, 5.0)
    assert coverage(fabricator) == 1.0 and coverage(honest) == pytest.approx(0.6)


def test_scorecard_shape():
    sc = scorecard([C] * 7 + [W] * 2 + [A] * 1)
    assert sc["n"] == 10 and sc["correct"] == 7 and sc["wrong"] == 2
    assert sc["coverage"] == pytest.approx(0.9)
    assert set(sc["net"]) == {f"lambda_{lam:g}" for lam in DEFAULT_LAMBDAS}
    assert sc["net"]["lambda_1"] == pytest.approx(0.5)   # (7−2)/10
    assert sc["crossover_lambda"] == pytest.approx(3.5)  # 7/2


def test_unknown_outcome_is_not_silently_a_pass():
    with pytest.raises(ValueError):
        net_score([C, "correct-ish"], 1.0)   # a bare string is not an Outcome
