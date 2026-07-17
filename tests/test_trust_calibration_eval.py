"""R&D — the trust-signal calibration harness measures the right thing.

The scientific property under test: the signal is calibrated only as far as its
observation of change is complete. With every knowledge-update observed
(unobserved_p=0) it is well-calibrated and barely over-trusts; blind to updates
(unobserved_p=1) it over-trusts obsolete facts and the Brier score rises. If this
property did NOT hold, the harness would be measuring noise.
"""
from __future__ import annotations

from verimem.contradiction import ContradictionStore
from verimem.semantic import SemanticMemory
from verimem.trust_calibration_eval import (
    evaluate_calibration,
    make_calibration_dataset,
    register_contradictions,
)

_NOW = 1_000_000_000.0


def _run(tmp_path, p: float, seed: int = 1):
    db = tmp_path / f"run_{int(p * 100)}_{seed}.db"
    sm = SemanticMemory(db_path=db)
    cs = ContradictionStore(db)
    ds = make_calibration_dataset(200, unobserved_p=p, now=_NOW, seed=seed)
    register_contradictions(ds, cs)
    return evaluate_calibration(ds, now=_NOW, contradiction_store=cs, sm=sm)


def test_full_observation_is_well_calibrated(tmp_path):
    r0 = _run(tmp_path, 0.0)
    # observed world: the dangerous failure (calling an unreliable fact trusted)
    # is essentially absent.
    assert r0.over_trust_rate < 0.05, (
        f"observed world should barely over-trust, got {r0.over_trust_rate}"
    )


def test_unobserved_updates_degrade_calibration(tmp_path):
    r0 = _run(tmp_path, 0.0)
    r1 = _run(tmp_path, 1.0)
    assert r1.brier > r0.brier, "blindness to updates must worsen Brier"
    assert r1.over_trust_rate > r0.over_trust_rate, (
        "blindness must increase dangerous over-trust of obsolete facts"
    )


def test_contested_path_fires(tmp_path):
    r0 = _run(tmp_path, 0.0)
    # ~15% of the dataset is contested and must be detected as such.
    assert r0.verdict_counts.get("contested", 0) > 0
