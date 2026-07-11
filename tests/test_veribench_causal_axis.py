"""VeriBench causal / do-query axis (#11) — provenance ≠ causality, defended λ*.

Flagship: test_defended_lambda_below_one — a floor-less trust-only store that has
corroborated a spurious correlation is net-NEGATIVE at the symmetric λ=1, so λ=1 is
a *defended* floor. Pure/hermetic (stdlib world, no model, no network).
"""
from __future__ import annotations

import pytest

from benchmark.veribench.axes import run_axis
from benchmark.veribench.causal_axis import (
    DIFFER,
    SAME,
    LatentConfoundWorld,
    build_causal_probes,
    defended_lambda,
    make_interv_sut,
    make_obs_sut,
    run_causal_axis,
)
from benchmark.veribench.scoring import Outcome, crossover_lambda, net_score

C, W, A = Outcome.CORRECT, Outcome.WRONG, Outcome.ABSTAIN


def test_world_do_has_no_effect():
    # observation is correlated; intervention leaves Y independent of the set X
    w = LatentConfoundWorld(seed=1, p_z=0.7, noise=0.1)
    n = 4000
    y_do1 = sum(w.intervene(1)[1] for _ in range(n)) / n
    y_do0 = sum(w.intervene(0)[1] for _ in range(n)) / n
    assert abs(y_do1 - y_do0) < 0.05          # do(X=1) vs do(X=0): SAME Y -> no effect
    assert abs(y_do1 - 0.7) < 0.06            # Y ~ p_z regardless of x_set


def test_observation_is_correlated_but_do_is_not():
    # point-Y is NON-separating: observation shows X~Y, intervention shows no effect
    w = LatentConfoundWorld(seed=2)
    n = 6000
    obs = [w.observe() for _ in range(n)]
    p_y_given_x1 = (sum(y for x, y in obs if x == 1) / max(1, sum(1 for x, _ in obs if x == 1)))
    p_y_given_x0 = (sum(y for x, y in obs if x == 0) / max(1, sum(1 for x, _ in obs if x == 0)))
    assert p_y_given_x1 - p_y_given_x0 > 0.3   # observationally X and Y move together
    y_do1 = sum(w.intervene(1)[1] for _ in range(n)) / n
    y_do0 = sum(w.intervene(0)[1] for _ in range(n)) / n
    assert abs(y_do1 - y_do0) < 0.05           # ...but the causal effect is zero


def test_confounded_items_have_none_gold():
    items = build_causal_probes(n_confounded=10, n_interventional=10)
    conf = [it for it in items if "conf#" in it.query]
    assert conf and all(it.gold is None for it in conf)
    ints = [it for it in items if "int#" in it.query]
    assert all(it.gold in (SAME, DIFFER) for it in ints)


def test_obs_sut_all_wrong_on_confounded():
    conf = build_causal_probes(n_confounded=20, n_interventional=0)
    out = run_axis(conf, make_obs_sut())
    assert out.count(W) == 20 and out.count(C) == 0   # confident + wrong on every one


def test_interv_sut_abstains_then_answers():
    items = build_causal_probes(n_confounded=15, n_interventional=25)
    golds = {it.query: it.gold for it in items}
    out = run_axis(items, make_interv_sut(golds))
    assert out.count(A) == 15                          # abstains on confounded
    assert out.count(C) == 25 and out.count(W) == 0    # correct on answerable


def test_defended_lambda_below_one():
    items = build_causal_probes(seed=0)
    obs = run_axis(items, make_obs_sut())
    c, w = obs.count(C), obs.count(W)
    a = c / (c + w)
    # closed form matches the empirical crossover (self-consistent, nothing hardcoded)
    assert crossover_lambda(obs) == pytest.approx(defended_lambda(a))
    assert 0.0 < defended_lambda(a) < 1.0              # λ=1 is a DEFENDED floor
    golds = {it.query: it.gold for it in items}
    interv = run_axis(items, make_interv_sut(golds))
    assert net_score(obs, 1.0) <= 0 < net_score(interv, 1.0)   # invisible→revealed at λ=1


def test_always_abstain_does_not_win():
    items = build_causal_probes(seed=0)

    def abstain_all(_q):
        return None

    out = run_axis(items, abstain_all)
    assert net_score(out, 1.0) == 0.0                  # safe but useless
    golds = {it.query: it.gold for it in items}
    interv = run_axis(items, make_interv_sut(golds))
    assert net_score(interv, 1.0) > net_score(out, 1.0)   # scope-aware beats abstain-all


def test_determinism():
    assert build_causal_probes(seed=0) == build_causal_probes(seed=0)
    r1, r2 = run_causal_axis(seed=0), run_causal_axis(seed=0)
    assert r1 == r2
    assert defended_lambda(0.3) == pytest.approx(0.3 / 0.7)
