"""Cycle 248 — adaptive_thresholds tests."""
from __future__ import annotations

from engram.adaptive_threshold import adaptive_thresholds


class TestAdaptiveThresholds:
    def test_baseline_below_1305(self) -> None:
        assert adaptive_thresholds(500) == (0.40, 0.20)
        assert adaptive_thresholds(1305) == (0.40, 0.20)

    def test_observed_anchor_1889(self) -> None:
        assert adaptive_thresholds(1889) == (0.20, 0.10)

    def test_extrapolation_5000(self) -> None:
        assert adaptive_thresholds(5000) == (0.10, 0.05)
        assert adaptive_thresholds(10000) == (0.10, 0.05)

    def test_monotonically_decreasing(self) -> None:
        sizes = [500, 1000, 1305, 1500, 1889, 2500, 5000, 10000]
        purities = [adaptive_thresholds(n)[0] for n in sizes]
        cohesions = [adaptive_thresholds(n)[1] for n in sizes]
        for i in range(1, len(purities)):
            assert purities[i] <= purities[i - 1]
            assert cohesions[i] <= cohesions[i - 1]

    def test_zero_and_negative_safe(self) -> None:
        assert adaptive_thresholds(0) == (0.40, 0.20)
        assert adaptive_thresholds(-1) == (0.40, 0.20)

    def test_interpolation_midpoint(self) -> None:
        """At n=1597 (midpoint between 1305 and 1889) purity should
        be ~0.3 and cohesion ~0.15."""
        purity, cohesion = adaptive_thresholds(1597)
        assert 0.29 <= purity <= 0.31
        assert 0.14 <= cohesion <= 0.16
