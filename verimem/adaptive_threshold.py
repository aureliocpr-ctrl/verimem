"""Cycle 248 (2026-05-23) — adaptive emergence thresholds.

Resolution of singolarità #21 (cycle 242/246): the cycle-233 default
(purity=0.4, cohesion=0.2) surfaces zero candidates on a corpus that
has grown past ~1500 facts because the master community disgregates.
At 1889 facts the operating point needs to drop to purity≈0.1-0.2.

This module ships a deterministic, monotonically-decreasing curve
that maps corpus size → (purity, cohesion) defaults. Auto-Dream
worker can call ``adaptive_thresholds(n_facts)`` instead of using
static defaults; the curve is calibrated against cycle 240/246
empirical sweeps.

A4 honest caveats:
- The curve is empirical, NOT theoretically motivated. Two anchor
  points only: cycle-170 baseline (1305 facts → 0.4) and cycle-246
  observation (1889 facts → 0.2).
- The cycle-184 anti-confab L1.8 gate + cycle-235 manual promote step
  still apply. Lower thresholds = more raw candidates, NOT more
  adopted skills.
- Real fix is probably a SECOND community detection pass over the
  master super-cluster (singolarità #21 deeper). Adaptive threshold
  is a TUNING patch, not the architectural cure.
"""
from __future__ import annotations


def adaptive_thresholds(n_facts: int) -> tuple[float, float]:
    """Return ``(min_topic_purity, min_cohesion)`` for the given corpus size.

    Anchor points (empirical):
      n ≤ 500   → (0.40, 0.20)
      n  1305   → (0.40, 0.20) (cycle 170 baseline)
      n  1889   → (0.20, 0.10) (cycle 246 observation)
      n ≥ 5000  → (0.10, 0.05) (extrapolation; revisit when reached)

    Curve: piecewise-linear interpolation.
    """
    n = int(n_facts) if n_facts and n_facts > 0 else 0
    if n <= 1305:
        return (0.40, 0.20)
    if n <= 1889:
        # Linear interpolation between (1305, 0.40) and (1889, 0.20).
        t = (n - 1305) / (1889 - 1305)
        purity = 0.40 - t * (0.40 - 0.20)
        cohesion = 0.20 - t * (0.20 - 0.10)
        return (round(purity, 3), round(cohesion, 3))
    if n <= 5000:
        # (1889, 0.20) → (5000, 0.10)
        t = (n - 1889) / (5000 - 1889)
        purity = 0.20 - t * (0.20 - 0.10)
        cohesion = 0.10 - t * (0.10 - 0.05)
        return (round(purity, 3), round(cohesion, 3))
    return (0.10, 0.05)


__all__ = ["adaptive_thresholds"]
