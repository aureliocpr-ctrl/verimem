"""R&D 2026-06-16 — calibration metrics for the trust-signal (pure, no Engram
state).

The trust-signal emits a categorical verdict (trusted/stale/contested/obsolete/
unverified). To ask "is it CALIBRATED" we map each verdict to an implied
probability of reliability and score it against a binary ground-truth outcome
(1 = the fact was actually reliable). These pure functions provide:

* ``brier_score``            — mean squared error of the implied probability;
* ``expected_calibration_error`` — weighted gap between confidence and accuracy;
* ``reliability_table``      — per-bin empirical reliability (the diagram data).

Exactly testable, so the harness's headline numbers rest on verifiable math.
"""
from __future__ import annotations

from collections.abc import Sequence


def _check(probs: Sequence[float], outcomes: Sequence[int]) -> None:
    if len(probs) != len(outcomes):
        raise ValueError(
            f"length mismatch: {len(probs)} probs vs {len(outcomes)} outcomes"
        )


def brier_score(probs: Sequence[float], outcomes: Sequence[int]) -> float:
    """Mean (p - outcome)^2. 0.0 = perfect, 1.0 = confidently wrong."""
    _check(probs, outcomes)
    if not probs:
        return 0.0
    return sum((float(p) - float(o)) ** 2 for p, o in zip(probs, outcomes, strict=True)) / len(probs)


def _bin_index(p: float, n_bins: int) -> int:
    if n_bins <= 0:
        return 0
    return min(int(float(p) * n_bins), n_bins - 1)


def reliability_table(
    probs: Sequence[float], outcomes: Sequence[int], *, n_bins: int = 10,
) -> list[dict]:
    """Per-bin reliability: (bin_lo, bin_hi, n, mean_pred, frac_positive)."""
    _check(probs, outcomes)
    if not probs or n_bins <= 0:
        return []
    agg = [{"sum_pred": 0.0, "sum_pos": 0, "n": 0} for _ in range(n_bins)]
    for p, o in zip(probs, outcomes, strict=True):
        b = agg[_bin_index(p, n_bins)]
        b["sum_pred"] += float(p)
        b["sum_pos"] += int(o)
        b["n"] += 1
    out: list[dict] = []
    for i, b in enumerate(agg):
        n = b["n"]
        out.append({
            "bin_lo": i / n_bins,
            "bin_hi": (i + 1) / n_bins,
            "n": n,
            "mean_pred": (b["sum_pred"] / n) if n else 0.0,
            "frac_positive": (b["sum_pos"] / n) if n else 0.0,
        })
    return out


def expected_calibration_error(
    probs: Sequence[float], outcomes: Sequence[int], *, n_bins: int = 10,
) -> float:
    """ECE: sum over bins of (n_bin / N) * |mean_pred - frac_positive|."""
    _check(probs, outcomes)
    if not probs:
        return 0.0
    total = len(probs)
    ece = 0.0
    for row in reliability_table(probs, outcomes, n_bins=n_bins):
        if row["n"]:
            ece += (row["n"] / total) * abs(row["mean_pred"] - row["frac_positive"])
    return ece


__all__ = ["brier_score", "expected_calibration_error", "reliability_table"]
