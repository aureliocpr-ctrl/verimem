"""Cycle 195 (2026-05-23) — decay_score tests.

RED marker: ``from engram.time_decay_score import decay_score`` must
fail on master.
"""
from __future__ import annotations

import math

import pytest

# RED MARKER
from engram.time_decay_score import (
    DEFAULT_HALF_LIFE_DAYS,
    DEFAULT_LINEAR_CUTOFF_DAYS,
    decay_score,
)


class TestDecayScore:
    # ---- Exponential ----------------------------------------------------

    def test_exp_at_zero_age_is_one(self) -> None:
        assert decay_score(0.0, curve="exp") == pytest.approx(1.0)

    def test_exp_at_half_life_is_half(self) -> None:
        out = decay_score(
            DEFAULT_HALF_LIFE_DAYS, curve="exp",
            half_life_days=DEFAULT_HALF_LIFE_DAYS,
        )
        assert out == pytest.approx(0.5, abs=1e-6)

    def test_exp_monotone_decreasing(self) -> None:
        a = decay_score(0, curve="exp")
        b = decay_score(7, curve="exp")
        c = decay_score(30, curve="exp")
        assert a > b > c > 0

    def test_exp_custom_half_life(self) -> None:
        out = decay_score(7.0, curve="exp", half_life_days=7.0)
        assert out == pytest.approx(0.5, abs=1e-6)

    # ---- Power ----------------------------------------------------------

    def test_power_at_zero_age_is_one(self) -> None:
        assert decay_score(0.0, curve="power") == pytest.approx(1.0)

    def test_power_monotone_decreasing(self) -> None:
        a = decay_score(0, curve="power", power_p=1.0)
        b = decay_score(10, curve="power", power_p=1.0)
        c = decay_score(100, curve="power", power_p=1.0)
        assert a > b > c > 0

    def test_power_p_zero_is_identity(self) -> None:
        """1 / (1+age)^0 == 1 for any age."""
        for age in (0, 1, 100, 1e6):
            assert decay_score(age, curve="power", power_p=0.0) == 1.0

    # ---- Linear ---------------------------------------------------------

    def test_linear_at_zero_is_one(self) -> None:
        assert decay_score(0.0, curve="linear") == pytest.approx(1.0)

    def test_linear_at_half_cutoff_is_half(self) -> None:
        out = decay_score(
            DEFAULT_LINEAR_CUTOFF_DAYS / 2.0,
            curve="linear",
            cutoff_days=DEFAULT_LINEAR_CUTOFF_DAYS,
        )
        assert out == pytest.approx(0.5, abs=1e-6)

    def test_linear_past_cutoff_is_zero(self) -> None:
        out = decay_score(
            DEFAULT_LINEAR_CUTOFF_DAYS * 2,
            curve="linear",
        )
        assert out == 0.0

    # ---- Defensive ------------------------------------------------------

    def test_negative_age_clamped_to_zero(self) -> None:
        """Future-dated facts (age < 0) treated as brand new (score 1)."""
        for curve in ("exp", "power", "linear"):
            assert decay_score(-10.0, curve=curve) == pytest.approx(1.0)

    def test_unknown_curve_returns_identity(self) -> None:
        assert decay_score(100.0, curve="banana") == 1.0  # type: ignore[arg-type]

    def test_bad_age_input_returns_identity(self) -> None:
        """Non-numeric age → 1.0, no crash."""
        assert decay_score("not a number") == 1.0  # type: ignore[arg-type]

    def test_zero_half_life_clamped(self) -> None:
        """half_life=0 would divide by zero; clamp to small epsilon."""
        out = decay_score(1.0, curve="exp", half_life_days=0.0)
        # Should not crash; exact value tends to 0 for any positive age
        # because lambda is huge.
        assert 0.0 <= out <= 1.0
        assert math.isfinite(out)

    def test_default_exp_matches_explicit(self) -> None:
        """Default curve='exp' must produce identical output to explicit."""
        a = decay_score(5.0)
        b = decay_score(5.0, curve="exp")
        assert a == pytest.approx(b)
