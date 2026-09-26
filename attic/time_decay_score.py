"""Cycle 195 (2026-05-23) — time-decay scoring primitive.

Closes gap §5 of docs/sota/temporal-evolution-narrative.md (cycle 192).
Pure function returning a multiplier in (0, 1] given an age in days
and a decay curve choice. Designed to be applied OUTSIDE the cosine
recall — caller multiplies base_score × decay(age_days).

Three curves (cycle-192 §2.1):
  * ``"exp"``     : exp(-λ · age_days),  λ = ln(2) / half_life_days
  * ``"power"``   : 1 / (1 + age_days)^p
  * ``"linear"``  : max(0, 1 - age_days / cutoff_days)

This module ships ONLY the decay scalar. Wiring into recall_hybrid
is scope of cycle 196.
"""
from __future__ import annotations

import math
from typing import Literal

DecayCurve = Literal["exp", "power", "linear"]

DEFAULT_HALF_LIFE_DAYS: float = 14.0
DEFAULT_POWER_P: float = 1.0
DEFAULT_LINEAR_CUTOFF_DAYS: float = 90.0


def decay_score(
    age_days: float,
    *,
    curve: DecayCurve = "exp",
    half_life_days: float = DEFAULT_HALF_LIFE_DAYS,
    power_p: float = DEFAULT_POWER_P,
    cutoff_days: float = DEFAULT_LINEAR_CUTOFF_DAYS,
) -> float:
    """Return a decay multiplier in [0, 1] for the given age.

    Args:
        age_days: time elapsed since the fact's ``created_at``.
            Negative ages are clamped to 0 (future-dated facts treated
            as "brand new").
        curve: one of ``"exp"`` / ``"power"`` / ``"linear"``.
        half_life_days: only for ``"exp"``. λ = ln(2) / half_life_days
            so decay(half_life_days) == 0.5.
        power_p: only for ``"power"``. Higher → faster decay.
        cutoff_days: only for ``"linear"``. After this, returns 0.

    Returns:
        Multiplier in [0, 1]. NEVER raises (defensive on bad inputs).
    """
    # Defensive: bad inputs return identity (1.0) rather than crash.
    try:
        age = max(0.0, float(age_days))
    except (TypeError, ValueError):
        return 1.0

    if curve == "exp":
        try:
            hl = max(1e-6, float(half_life_days))
        except (TypeError, ValueError):
            hl = DEFAULT_HALF_LIFE_DAYS
        lam = math.log(2.0) / hl
        return float(math.exp(-lam * age))

    if curve == "power":
        try:
            p = max(0.0, float(power_p))
        except (TypeError, ValueError):
            p = DEFAULT_POWER_P
        return float(1.0 / ((1.0 + age) ** p))

    if curve == "linear":
        try:
            cut = max(1e-6, float(cutoff_days))
        except (TypeError, ValueError):
            cut = DEFAULT_LINEAR_CUTOFF_DAYS
        return float(max(0.0, 1.0 - age / cut))

    # Unknown curve → identity (defensive).
    return 1.0


__all__ = [
    "decay_score",
    "DecayCurve",
    "DEFAULT_HALF_LIFE_DAYS",
    "DEFAULT_POWER_P",
    "DEFAULT_LINEAR_CUTOFF_DAYS",
]
