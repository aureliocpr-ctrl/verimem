"""A threshold read from the environment must be a NUMBER, not `nan`.

`float("nan")` does not raise, so `try: float(env) except ValueError` lets it
through — and every comparison against NaN is False. A gate whose threshold is
NaN therefore never fires: `score < threshold` is False for every score, so
nothing is ever quarantined, held, or refused. The guard is still in the code,
still covered by tests, and silently does nothing. `inf` and `-inf` are the
same class from the other direction: one blocks everything, the other admits it.

Found by a design review on the composer floor (2026-07-28) and then MEASURED
across the package: 16 of 18 (threshold × poison) combinations accepted the
value. These are not exotic thresholds — they are the write gate
(ENGRAM_INGEST_GROUND_THRESHOLD), the CE uncertainty band (VERIMEM_CE_TAU_HI),
the self-provenance quota that enforces P85 (ENGRAM_SELF_RATIO_MAX), per-source
trust (ENGRAM_SOURCE_TRUST_MIN) and the composer floor, which is always on.

A malformed value is operator error and stays recoverable: fall back to the
declared default rather than to a silently disarmed gate. Note the failure is
NOT hypothetical-only in shape — `max(0.0, float(raw))` happens to filter NaN
while `max(float(raw), 0.0)` does not, so which sites were safe was an accident
of argument order, not a decision.
"""
from __future__ import annotations

import math

import pytest

# (module, callable, env var, what the threshold governs)
THRESHOLDS = [
    ("verimem.composer", "_min_score", "ENGRAM_COMPOSER_MIN_SCORE"),
    ("verimem.grounding_gate", "_ce_band_tau_hi", "VERIMEM_CE_TAU_HI"),
    ("verimem.self_provenance", "_threshold", "ENGRAM_SELF_RATIO_MAX"),
    ("verimem.source_trust", "threshold", "ENGRAM_SOURCE_TRUST_MIN"),
    ("verimem.conversation_ingest", "_ingest_ground_threshold",
     "ENGRAM_INGEST_GROUND_THRESHOLD"),
]


@pytest.mark.parametrize("mod_name,fn_name,env", THRESHOLDS)
@pytest.mark.parametrize("poison", ["nan", "NaN", "inf", "-inf", "infinity"])
def test_threshold_rejects_non_finite_env(mod_name, fn_name, env, poison,
                                          monkeypatch):
    import importlib
    fn = getattr(importlib.import_module(mod_name), fn_name)
    monkeypatch.delenv(env, raising=False)
    default = fn()
    monkeypatch.setenv(env, poison)
    got = fn()
    assert math.isfinite(got), (
        f"{mod_name}.{fn_name}() returned {got} for {env}={poison!r} — a gate "
        f"with a non-finite threshold never fires and says nothing")
    assert got == default, (
        f"a malformed {env} must fall back to the declared default {default}, "
        f"got {got}")


def test_relevance_floor_rejects_infinity(monkeypatch):
    """env_floor survived nan by accident (max(0.0, nan) == 0.0) but not inf —
    an infinite relevance floor abstains on every query ever asked."""
    from verimem.relevance_floor import env_floor
    monkeypatch.setenv("ENGRAM_MIN_RELEVANCE", "inf")
    got = env_floor("ENGRAM_MIN_RELEVANCE")
    assert got == 0.0 or (isinstance(got, float) and math.isfinite(got)), got


def test_valid_values_still_pass(monkeypatch):
    """The guard must not become a wall: real overrides keep working."""
    from verimem.composer import _min_score
    monkeypatch.setenv("ENGRAM_COMPOSER_MIN_SCORE", "72.5")
    assert _min_score() == 72.5
    from verimem.source_trust import threshold
    monkeypatch.setenv("ENGRAM_SOURCE_TRUST_MIN", "0.4")
    assert threshold() == 0.4
