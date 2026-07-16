"""AdaptiveLedger — REMORSE graft, phase-1 SHADOW (handoff fact ab53896fe93e,
Code/remorse/HANDOFF-VERIMEM.md, 2026-07-16). Per-tenant, per-domain self-trust
learned online: 3 experts (lessons@14d, exposure, hazard@14d with the lab's
exact smoothing), weights exp(eta*MRR) eta=3, fixed-share alpha=0.05 applied
per-WINDOW only, UNIFORM cold start. Every rule below has a falsification
behind it in the lab (PREDICTIONS.md) — these tests pin the graft's contract:

* decay: an old error weighs less (half-life), a future event is invisible;
* cold start is UNIFORM (no kNN profiling — refuted at +37% regret);
* anti-poisoning: an unverified external error report weighs 0.2;
* fixed-share keeps every expert alive (weight floor alpha/k);
* the shadow wrapper NEVER raises out of observe/decide (log-only safety).
"""
from __future__ import annotations

import math

from engram.adaptive_ledger import (
    DAY,
    AdaptiveMeta,
    ConsequenceLedger,
    ShadowLedger,
)


def test_consequence_decay_and_future_invisible():
    led = ConsequenceLedger(half_life_days=14.0)
    led.record(t=0.0, domain="db", weight=1.0)
    assert led.mass("db", now=0.0) == 1.0
    # one half-life later the mass is halved
    assert abs(led.mass("db", now=14 * DAY) - 0.5) < 1e-9
    # future events are invisible to the ledger
    led.record(t=100 * DAY, domain="db", weight=5.0)
    assert abs(led.mass("db", now=14 * DAY) - 0.5) < 1e-9


def test_meta_cold_start_uniform_weights():
    meta = AdaptiveMeta()
    assert meta.weights == {"lessons_only": 1 / 3,
                            "exposure_only": 1 / 3,
                            "hazard_x_exposure": 1 / 3}


def test_meta_window_update_expeta_mrr_and_fixed_share():
    meta = AdaptiveMeta(eta=3.0, alpha=0.05)
    # a window where lessons_only was perfect (MRR 1) and the others useless
    meta.update_window({"lessons_only": 1.0, "exposure_only": 0.0,
                        "hazard_x_exposure": 0.0})
    w = meta.weights
    assert w["lessons_only"] > w["exposure_only"] == w["hazard_x_exposure"]
    # fixed-share floor: no expert ever dies below alpha/k
    for _ in range(50):
        meta.update_window({"lessons_only": 1.0, "exposure_only": 0.0,
                            "hazard_x_exposure": 0.0})
    assert min(meta.weights.values()) >= 0.05 / 3 - 1e-12
    assert abs(sum(meta.weights.values()) - 1.0) < 1e-9


def test_shadow_exposure_and_hazard_smoothing():
    s = ShadowLedger()
    now = 1000.0 * DAY
    # 10 recalls on topic 'db', no confirmed error → low hazard (smoothed prior)
    for _ in range(10):
        s.observe_recall("t1", ["db"], now=now)
    d0 = s.decision("t1", "db", now=now)
    # lab smoothing: (num+0.25)/(den+5.0) — with num=0, den=10 → ~0.0167
    assert d0["hazard"] < 0.05
    # a confirmed error raises the hazard for THAT tenant+topic only
    s.observe_error("t1", "db", now=now)
    d1 = s.decision("t1", "db", now=now)
    assert d1["hazard"] > d0["hazard"]
    # tenant isolation: t2 never saw t1's error — it sits exactly at the
    # never-seen smoothed prior (0.25/5.0 = 0.05, "possible, never certain"),
    # NOT at t1's post-error rate. NB the prior is deliberately ABOVE a clean
    # 10-exposure track record (0.0167): no track record ≠ trusted.
    other = s.decision("t2", "db", now=now)
    assert math.isclose(other["hazard"], 0.25 / 5.0, rel_tol=1e-6)
    assert other["hazard"] < d1["hazard"]


def test_shadow_anti_poisoning_external_weight():
    s = ShadowLedger()
    now = 2000.0 * DAY
    s.observe_recall("t1", ["api"], now=now)
    s.observe_error("t1", "api", now=now, external=True)   # unverified report
    h_ext = s.decision("t1", "api", now=now)["hazard"]
    s2 = ShadowLedger()
    s2.observe_recall("t1", ["api"], now=now)
    s2.observe_error("t1", "api", now=now)                  # confirmed
    h_conf = s2.decision("t1", "api", now=now)["hazard"]
    assert h_ext < h_conf                                    # 0.2 vs 1.0 mass
    assert math.isclose((h_ext - _prior()) / max(h_conf - _prior(), 1e-12),
                        0.2, rel_tol=0.35)                   # ~one fifth the lift


def _prior() -> float:
    # hazard smoothing prior with num=0, den=1: 0.25/6.0 scaled by exposure 1
    return 0.25 / 6.0


def test_shadow_never_raises_from_observe_or_decide():
    s = ShadowLedger()
    # garbage in → no exception out (shadow must never break a request)
    s.observe_recall(None, None, now=None)          # type: ignore[arg-type]
    s.observe_error("", "", now=float("nan"))
    out = s.decision("", "", now=0.0)
    assert isinstance(out, dict) and "hazard" in out and "advice" in out
