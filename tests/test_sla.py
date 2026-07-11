"""Error-cost → abstention SLA (Verimem product #3) — TDD.

The through-line under test: the product's abstention threshold λ/(1+λ) IS the
VeriBench NET(λ) break-even accuracy, so one λ means the same thing end to end.
"""
from __future__ import annotations

import pytest

from benchmark.veribench.scoring import Outcome, net_score
from engram.sla import answer_threshold, error_cost, should_answer


def test_threshold_closed_form():
    assert answer_threshold(1.0) == pytest.approx(0.5)      # symmetric
    assert answer_threshold(5.0) == pytest.approx(5 / 6)    # 0.833: abstain unless sure
    assert answer_threshold(10.0) == pytest.approx(10 / 11)  # 0.909
    assert answer_threshold(0.25) == pytest.approx(0.2)     # silence costs more


def test_threshold_monotone_in_lambda():
    lams = [0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 100.0]
    ts = [answer_threshold(x) for x in lams]
    assert ts == sorted(ts)                                 # higher λ -> abstain more
    assert all(0.0 <= t < 1.0 for t in ts)


def test_should_answer_boundary_is_strict():
    thr = answer_threshold(5.0)
    assert should_answer(thr + 1e-6, 5.0) is True
    assert should_answer(thr, 5.0) is False                 # exactly break-even -> abstain
    assert should_answer(thr - 1e-6, 5.0) is False


def test_env_knob(monkeypatch):
    monkeypatch.setenv("ENGRAM_ERROR_COST", "5")
    assert error_cost() == 5.0
    assert answer_threshold() == pytest.approx(5 / 6)       # None -> reads the knob
    monkeypatch.delenv("ENGRAM_ERROR_COST", raising=False)
    assert error_cost() == 1.0                              # default symmetric


def test_bad_or_nonpositive_knob_fails_safe(monkeypatch):
    for bad in ("not-a-number", "0", "-3"):
        monkeypatch.setenv("ENGRAM_ERROR_COST", bad)
        assert error_cost() == 1.0                          # never a 0/negative λ


def test_threshold_is_the_veribench_net_breakeven():
    """A store answering with accuracy ``a`` on its answered items nets positive iff
    a > λ/(1+λ). So tuning to answer_threshold(λ) maximises the VeriBench NET(λ)."""
    n = 2000
    for lam in (1.0, 3.0, 5.0, 10.0):
        thr = answer_threshold(lam)
        for a, want_positive in ((thr + 0.03, True), (thr - 0.03, False)):
            c = round(a * n)
            outs = [Outcome.CORRECT] * c + [Outcome.WRONG] * (n - c)
            assert (net_score(outs, lam) > 0) is want_positive
