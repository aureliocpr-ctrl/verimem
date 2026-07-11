"""VeriBench adversarial-trust axis (#11 flagship) — collusion + trusted-sleeper.

The capstone claim as tests: naive source-counting is fooled by collusion; an
independence-aware consistency channel defends collusion but is fooled by the
sleeper; only ``min(consistency, outcome)`` — the two channels — is net-positive
across BOTH attacks. Drives the REAL engram.source_trust.SourceTrustBook.
"""
from __future__ import annotations

from benchmark.veribench.adversarial_axis import (
    build_adversarial_probes,
    make_both_arm,
    make_consistency_arm,
    make_naive_arm,
    run_adversarial_axis,
)
from benchmark.veribench.axes import run_axis
from benchmark.veribench.scoring import Outcome

C, W, A = Outcome.CORRECT, Outcome.WRONG, Outcome.ABSTAIN


def _of_kind(items, kind):
    return [it for it in items if f"/{kind}#" in it.query]


def test_naive_count_fooled_by_collusion():
    items, by_q = build_adversarial_probes(n_each=10)
    out = run_axis(_of_kind(items, "collusion"), make_naive_arm(by_q))
    assert out.count(W) == 10          # accepts the false colluded value every time


def test_independence_defends_collusion():
    items, by_q = build_adversarial_probes(n_each=10)
    out = run_axis(_of_kind(items, "collusion"), make_consistency_arm(by_q))
    assert W not in out                # copies collapse to one witness -> never wrong


def test_consistency_only_fooled_by_sleeper():
    items, by_q = build_adversarial_probes(n_each=10)
    out = run_axis(_of_kind(items, "sleeper"), make_consistency_arm(by_q))
    assert out.count(W) == 10          # genuine high consistency -> trusts the lie


def test_outcome_channel_defends_sleeper():
    items, by_q = build_adversarial_probes(n_each=10)
    out = run_axis(_of_kind(items, "sleeper"), make_both_arm(by_q))
    assert W not in out                # the failed-in-use outcome bites through min


def test_legit_items_accepted_by_every_arm():
    items, by_q = build_adversarial_probes(n_each=10)
    leg = _of_kind(items, "legit")
    for make in (make_naive_arm, make_consistency_arm, make_both_arm):
        assert run_axis(leg, make(by_q)).count(C) == 10   # real corroboration passes


def test_only_two_channels_net_positive_at_high_lambda():
    r = run_adversarial_axis(n_each=20)
    net5 = {k: v["net"]["lambda_5"] for k, v in r.items()}
    assert net5["min_both"] > 0                    # the only arm that survives both
    assert net5["naive_count"] < 0                 # collusion sinks it
    assert net5["consistency_only"] < 0            # the sleeper sinks it
    assert net5["min_both"] == max(net5.values())


def test_determinism():
    assert run_adversarial_axis(n_each=5) == run_adversarial_axis(n_each=5)
