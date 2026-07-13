"""VeriBench real-corpus outcome mapping — the load-bearing honesty of the bench.

If this truth table is wrong, every headline number is wrong, so it is pinned
here explicitly, plus a discrimination check: an honest system must stay
NET-positive as λ rises where a fabricator collapses.
"""
from __future__ import annotations

from benchmark.veribench.real_axis import (
    answerable_outcome,
    outcomes_for_system,
    unanswerable_outcome,
)
from benchmark.veribench.scoring import Outcome, net_score, scorecard


def test_answerable_truth_table():
    assert answerable_outcome(hit=True, abstained=False) == Outcome.CORRECT
    assert answerable_outcome(hit=False, abstained=False) == Outcome.WRONG
    assert answerable_outcome(hit=True, abstained=True) == Outcome.ABSTAIN
    assert answerable_outcome(hit=False, abstained=True) == Outcome.ABSTAIN


def test_unanswerable_truth_table():
    assert unanswerable_outcome(abstained=True) == Outcome.ABSTAIN     # honest
    assert unanswerable_outcome(abstained=False) == Outcome.WRONG      # fabrication


def test_outcomes_for_system_maps_both_halves():
    ans = [{"retrieval_hit": True, "abstained": False},    # CORRECT
           {"retrieval_hit": False, "abstained": False},   # WRONG
           {"retrieval_hit": True, "abstained": True}]      # ABSTAIN
    unans = [{"abstained": True},                            # ABSTAIN
             {"abstained": False}]                           # WRONG
    got = outcomes_for_system(ans, unans)
    assert got == [Outcome.CORRECT, Outcome.WRONG, Outcome.ABSTAIN,
                   Outcome.ABSTAIN, Outcome.WRONG]


def test_abstention_beats_fabrication_as_lambda_rises():
    """The thesis, made a number. Same answerable performance (both nail 5/5);
    they differ ONLY on 5 unanswerable probes: honest abstains, fabricator commits.
    recall@k (correct/n) is identical; NET(λ) separates them and the gap widens."""
    ans_ok = [{"retrieval_hit": True, "abstained": False}] * 5
    honest = outcomes_for_system(ans_ok, [{"abstained": True}] * 5)
    fabricator = outcomes_for_system(ans_ok, [{"abstained": False}] * 5)

    # coverage-blind recall@k cannot tell them apart
    assert sum(o == Outcome.CORRECT for o in honest) == \
           sum(o == Outcome.CORRECT for o in fabricator) == 5

    # NET(λ): equal-ish at λ=1, honest pulls decisively ahead as wrong costs more
    assert net_score(honest, 1.0) > net_score(fabricator, 1.0)
    assert net_score(honest, 5.0) > net_score(fabricator, 5.0)
    gap1 = net_score(honest, 1.0) - net_score(fabricator, 1.0)
    gap5 = net_score(honest, 5.0) - net_score(fabricator, 5.0)
    assert gap5 > gap1                                   # the λ-sweep is the point
    # the fabricator goes net-negative under a high stake; the honest one never does
    assert net_score(fabricator, 5.0) < 0 <= net_score(honest, 5.0)
    assert scorecard(honest)["crossover_lambda"] is None  # no wrong answers ever


def test_scrambled_negative_control_collapses():
    """Validity: if retrieval is destroyed (no hits) but the system still commits,
    CORRECT must go to zero — proving a headline CORRECT is real retrieval, not
    an artifact of the harness."""
    scrambled = outcomes_for_system(
        [{"retrieval_hit": False, "abstained": False}] * 10, [])
    assert all(o == Outcome.WRONG for o in scrambled)
    assert scorecard(scrambled)["correct"] == 0
