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
    # The two the first sweep missed, in a module it had already touched. An
    # adversarial reviewer flagged them as harmless because `score >= nan` is
    # False and therefore fail-CLOSED. That is true at four call sites and
    # WRONG at the two that answer the user: client.py:710 reads
    # `judge_score < _resolve_threshold(None)` to return "NO ANSWER", and
    # trust_report.py:217 reads `score < _resolve_threshold(None)` to drop the
    # hits. With NaN both comparisons are False, so the answer the judge would
    # have rejected is SERVED. Same poison, opposite sign, depending on which
    # way the comparison is written — which is exactly why the parser, not the
    # call site, has to be the thing that refuses it.
    ("verimem.grounding_gate", "_resolve_write_threshold",
     "ENGRAM_GROUNDING_WRITE_THRESHOLD"),
    # Found by an adversarial design review the same day this module was
    # written, on the module's OWN docstring: it claimed "one parser, one
    # contract" for "every threshold in this package" after migrating six of
    # twenty-two call sites. The worst survivor is the CE relevance floor —
    # trust_report._apply_ce_gate keeps a hit when `score >= floor`, so
    # VERIMEM_CE_RELEVANCE_FLOOR=-inf keeps EVERY hit and the trust report
    # serves the nearest-but-wrong fact as trusted, which is the confabulation
    # the product exists to refuse.
    ("verimem.trust_report", "_ce_relevance_floor", "VERIMEM_CE_RELEVANCE_FLOOR"),
    ("verimem.truth_reconciliation", "_min_conflict_overlap",
     "ENGRAM_RECONCILE_MIN_OVERLAP"),
    ("verimem.semantic", "_topic_penalty_strength", "ENGRAM_TOPIC_PENALTY"),
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


@pytest.mark.parametrize("poison", ["nan", "inf", "-inf"])
def test_answer_threshold_rejects_non_finite_env(poison, monkeypatch):
    """ENGRAM_GROUNDING_THRESHOLD gates the ANSWER path, where the comparison is
    written `judge_score < threshold` — so a NaN does not build a wall, it opens
    the door: the answer the judge rejected gets served."""
    from verimem.grounding_gate import _resolve_threshold
    monkeypatch.delenv("ENGRAM_GROUNDING_THRESHOLD", raising=False)
    default = _resolve_threshold(None)
    monkeypatch.setenv("ENGRAM_GROUNDING_THRESHOLD", poison)
    got = _resolve_threshold(None)
    assert math.isfinite(got) and got == default, (
        f"ENGRAM_GROUNDING_THRESHOLD={poison!r} resolved to {got}: every "
        f"`score < threshold` rejection silently stops firing")


@pytest.mark.parametrize("poison", [float("nan"), float("inf")])
def test_an_explicit_non_finite_argument_is_refused_too(poison):
    """The env is not the only way in — a caller can pass the threshold."""
    from verimem.grounding_gate import _resolve_threshold
    assert math.isfinite(_resolve_threshold(poison))


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
