"""Cycle #63 — Test pure logic of time decay applied to cosine similarity.

The decay penalises facts proportional to their age (in days), with a grace
period and a hard cap. Used by the embedding daemon to push stale facts
down the ranking without re-encoding the corpus.

Design (cycle #63 hard-negative analysis):
  - grace_days: no penalty under this age (default 3.0)
  - per_day:    penalty rate after grace (default 0.05 = -5%/day)
  - cap:        max penalty (default 0.20 = -20%)
  - applied multiplicatively: adj_sim = sim * (1 - penalty)

These tests are PURE (no sqlite, no encoder, no socket). They lock down the
math of the decay function so the daemon never silently regresses.
"""
from __future__ import annotations

import numpy as np
import pytest

from engram.decay import apply_time_decay

SEC_PER_DAY = 86400.0


def test_decay_no_penalty_within_grace_period():
    """Facts younger than grace_days must keep original score."""
    now = 1_000_000.0
    sims = np.array([0.8, 0.7], dtype=np.float32)
    ats = np.array([now - 0 * SEC_PER_DAY, now - 2.5 * SEC_PER_DAY])
    adj = apply_time_decay(
        sims, ats, now=now,
        grace_days=3.0, per_day=0.05, cap=0.20,
    )
    np.testing.assert_allclose(adj, sims, rtol=1e-6)


def test_decay_linear_after_grace():
    """A fact 5 days old → 2 days past grace → -10% penalty."""
    now = 1_000_000.0
    sims = np.array([1.0], dtype=np.float32)
    ats = np.array([now - 5.0 * SEC_PER_DAY])
    adj = apply_time_decay(
        sims, ats, now=now,
        grace_days=3.0, per_day=0.05, cap=0.20,
    )
    # 5 - 3 = 2 days * 0.05 = 0.10 penalty → 1.0 * 0.90 = 0.90
    np.testing.assert_allclose(adj, [0.90], rtol=1e-5)


def test_decay_capped_at_max():
    """A fact 30 days old must still cap at the configured maximum penalty."""
    now = 1_000_000.0
    sims = np.array([1.0], dtype=np.float32)
    ats = np.array([now - 30.0 * SEC_PER_DAY])
    adj = apply_time_decay(
        sims, ats, now=now,
        grace_days=3.0, per_day=0.05, cap=0.20,
    )
    # Even though raw penalty would be (30-3)*0.05 = 1.35, capped at 0.20
    # so adj = 1.0 * (1 - 0.20) = 0.80
    np.testing.assert_allclose(adj, [0.80], rtol=1e-5)


def test_decay_preserves_ordering_when_uniform_age():
    """Two facts of the same age must keep their original cosine ordering."""
    now = 1_000_000.0
    sims = np.array([0.8, 0.5], dtype=np.float32)
    ats = np.array([now - 10 * SEC_PER_DAY, now - 10 * SEC_PER_DAY])
    adj = apply_time_decay(sims, ats, now=now)
    assert adj[0] > adj[1]  # ordering preserved


def test_decay_flips_ranking_for_stale_vs_recent():
    """Cycle #63 motivating case: a slightly-better cosine but old fact
    should be overtaken by a slightly-worse cosine recent fact.
    This is exactly MISS #4 of bench v2 (stale status report 2026-05-11
    vs cycle #51 docs 2026-05-14)."""
    now = 1_000_000.0
    # Stale-but-better-cosine vs fresh-but-slightly-worse
    sims = np.array([0.55, 0.50], dtype=np.float32)
    ats = np.array([
        now - 6.0 * SEC_PER_DAY,    # 6 days old → penalty (6-3)*0.05=0.15
        now - 0.5 * SEC_PER_DAY,    # within grace, no penalty
    ])
    adj = apply_time_decay(sims, ats, now=now)
    # adj[0] = 0.55 * 0.85 = 0.4675
    # adj[1] = 0.50 * 1.00 = 0.50
    assert adj[1] > adj[0], (
        f"Recent fact should beat stale: adj[recent]={adj[1]:.4f} "
        f"adj[stale]={adj[0]:.4f}"
    )


def test_decay_disabled_when_per_day_zero():
    """Setting per_day=0 must produce a no-op decay regardless of age."""
    now = 1_000_000.0
    sims = np.array([0.8, 0.5], dtype=np.float32)
    ats = np.array([now - 100 * SEC_PER_DAY, now - 0.1 * SEC_PER_DAY])
    adj = apply_time_decay(
        sims, ats, now=now, grace_days=0.0, per_day=0.0, cap=0.20,
    )
    np.testing.assert_allclose(adj, sims, rtol=1e-6)


def test_decay_handles_future_timestamps_safely():
    """Defensive: if a fact has a timestamp slightly in the future
    (clock skew), age is clamped to 0 → no penalty, no negative penalty."""
    now = 1_000_000.0
    sims = np.array([0.8], dtype=np.float32)
    ats = np.array([now + 5 * SEC_PER_DAY])  # 5 days in the future
    adj = apply_time_decay(sims, ats, now=now)
    np.testing.assert_allclose(adj, sims, rtol=1e-6)


def test_decay_empty_input_returns_empty():
    """Edge case: empty arrays produce empty result without error."""
    now = 1_000_000.0
    sims = np.array([], dtype=np.float32)
    ats = np.array([])
    adj = apply_time_decay(sims, ats, now=now)
    assert adj.shape == (0,)
