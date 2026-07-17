"""Tests for FORGIA pezzo #12: TCM contextual reinstatement.

Howard & Kahana (2002) "A distributed representation of temporal
context" (DOI 10.1006/jmps.2001.1388) shows that human episodic
memory is indexed by a *drifting context vector* — a continuous
state that evolves with each new observation. Encoding a memory
binds it to the context AT THAT MOMENT; retrieval works best when
the current context matches the encoding context (Tulving's
"encoding specificity principle", Tulving & Thomson 1973).

Math:
    context_t = ρ · context_{t-1} + (1 - ρ) · obs_emb_t      (drift)

  - ρ ∈ [0, 1]: persistence. ρ=1 → frozen, ρ=0 → no memory of past.
  - Empirical sweet spot from cognitive lit: ρ ≈ 0.85.

For HippoAgent: the wake loop streams observations through a
ContextEngine; at episode-store time the current context vector is
saved alongside the episode. At recall time, the caller can supply
the current context and a `context_weight`, and the retrieval scores
become:
    score = β_q · cosine(query, ep.summary) + β_c · cosine(context, ep.context)

Three measurable invariants we test (declared BEFORE implementing):

  1. DRIFT: feeding observations one by one moves the context vector
     monotonically toward the most-recent observation but retains
     traces of older ones (intermediate cosine).

  2. STEADY STATE under repetition: feeding the same observation N
     times converges the context to that observation (cosine → 1).

  3. RESET: explicitly resetting the context returns it to a known
     zero or seed state.
"""
from __future__ import annotations

import numpy as np
import pytest


def _normalize(v: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(v))
    return v / n if n > 0 else v


# ---------- Test 1: drift moves toward recent observation ---------------


def test_drift_moves_context_toward_recent_obs():
    from verimem.context_engine import ContextEngine

    rng = np.random.default_rng(seed=1)
    a = _normalize(rng.standard_normal(64).astype(np.float32))
    b = _normalize(rng.standard_normal(64).astype(np.float32))

    eng = ContextEngine(dim=64, rho=0.85)
    eng.observe(a)
    state_after_a = eng.state.copy()
    cos_a_initial = float(np.dot(state_after_a, a))

    # 5 successive observations of `b` — context should drift toward `b`.
    for _ in range(5):
        eng.observe(b)
    state_after_5b = eng.state.copy()
    cos_b_after = float(np.dot(state_after_5b, b))
    cos_a_after = float(np.dot(state_after_5b, a))

    assert cos_b_after > cos_a_after, (
        "drift didn't move context toward recent obs"
    )
    # Majority alignment: with ρ=0.85 + 5 b-observations the integrated
    # drift weight on b is ~0.65 vs trace of a ~0.07. The actual cosine
    # depends on the angle between random `a` and `b` (~0 here), so we
    # check the ordering and a moderate threshold rather than pinning
    # an exact number.
    assert cos_b_after > 0.4
    # Some trace of a remains — drift, not replace.
    assert cos_a_after > 0.0


# ---------- Test 2: steady state under repetition -----------------------


def test_steady_state_with_repeated_observation():
    from verimem.context_engine import ContextEngine

    rng = np.random.default_rng(seed=2)
    obs = _normalize(rng.standard_normal(32).astype(np.float32))

    eng = ContextEngine(dim=32, rho=0.85)
    for _ in range(50):
        eng.observe(obs)
    cos = float(np.dot(eng.state, obs))
    # After 50 repetitions, context is essentially the obs.
    assert cos > 0.99


# ---------- Test 3: reset returns to known state ------------------------


def test_reset_returns_to_zero_state():
    from verimem.context_engine import ContextEngine

    rng = np.random.default_rng(seed=3)
    obs = _normalize(rng.standard_normal(16).astype(np.float32))

    eng = ContextEngine(dim=16, rho=0.85)
    eng.observe(obs)
    eng.observe(obs)
    assert float(np.linalg.norm(eng.state)) > 0.0
    eng.reset()
    assert float(np.linalg.norm(eng.state)) == pytest.approx(0.0, abs=1e-6)


# ---------- Test 4: initial state is well-defined -----------------------


def test_initial_state_is_zero_norm_or_seeded():
    from verimem.context_engine import ContextEngine

    eng = ContextEngine(dim=16, rho=0.85)
    # Default: zero state — first observation IS the context after one step.
    assert float(np.linalg.norm(eng.state)) == 0.0


# ---------- Test 5: rho=1 freezes the context ---------------------------


def test_rho_one_freezes_context():
    """ρ=1 means the new observation contributes 0 — the context never
    moves. Edge case kept correct for tuning."""
    from verimem.context_engine import ContextEngine

    rng = np.random.default_rng(seed=4)
    a = _normalize(rng.standard_normal(8).astype(np.float32))
    b = _normalize(rng.standard_normal(8).astype(np.float32))

    eng = ContextEngine(dim=8, rho=1.0)
    eng.observe(a)
    state1 = eng.state.copy()
    eng.observe(b)
    state2 = eng.state.copy()
    assert np.allclose(state1, state2)


# ---------- Test 6: rho=0 makes context = latest obs --------------------


def test_rho_zero_makes_context_equal_latest():
    """ρ=0 means the context is just the latest observation — useful
    for "fully-reactive" tasks where memory of the past is harmful."""
    from verimem.context_engine import ContextEngine

    rng = np.random.default_rng(seed=5)
    a = _normalize(rng.standard_normal(8).astype(np.float32))
    b = _normalize(rng.standard_normal(8).astype(np.float32))

    eng = ContextEngine(dim=8, rho=0.0)
    eng.observe(a)
    eng.observe(b)
    assert np.allclose(eng.state, b)


# ---------- Test 7: dimension mismatch raises ---------------------------


def test_observation_with_wrong_dim_raises():
    """Defensive: feeding an observation of the wrong dimensionality
    should fail loudly, not silently corrupt the context vector."""
    from verimem.context_engine import ContextEngine

    eng = ContextEngine(dim=8, rho=0.85)
    bad = np.zeros(16, dtype=np.float32)
    with pytest.raises(ValueError, match="dim"):
        eng.observe(bad)
