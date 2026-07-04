"""Phase-0 statistics primitives for the epistemic research program.

Every headline number in this program must carry a confidence interval and, when we claim
one signal beats another, a significance test. This module is the single home for that
machinery so no experiment hand-rolls (and mis-implements) it again — the tie-biased AUROC
bug that manufactured a fake result is the reason this exists.

Pure functions, numpy only, deterministic (seeded). No LLM, no network.

- ``auroc``            tie-corrected Mann-Whitney AUC (average ranks)
- ``aurc``             area under the risk-coverage curve (selective-prediction scalar)
- ``bootstrap_ci``     percentile CI for any metric over resampled (score,label) pairs
- ``ece``              expected calibration error (reliability binning)
- ``delong_test``      DeLong p-value for two CORRELATED AUCs (same samples, two scores)
"""
from __future__ import annotations

import math
import random
from collections.abc import Callable

import numpy as np


def auroc(scores: list[float] | np.ndarray, labels: list[int] | np.ndarray) -> float:
    """Tie-corrected Mann-Whitney AUC (label 1 = positive). NaN if one class is empty."""
    s = np.asarray(scores, float)
    y = np.asarray(labels, int)
    n_pos = int((y == 1).sum())
    n_neg = int((y == 0).sum())
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    order = np.argsort(s, kind="mergesort")
    s_sorted = s[order]
    ranks = np.empty(len(s), float)
    i = 0
    while i < len(s_sorted):
        j = i
        while j + 1 < len(s_sorted) and s_sorted[j + 1] == s_sorted[i]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2.0 + 1.0
        i = j + 1
    r_pos = float(ranks[y == 1].sum())
    return float((r_pos - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg))


def aurc(scores: list[float] | np.ndarray, correct: list[int] | np.ndarray) -> float:
    """Area under the risk-coverage curve: accept highest-score first, risk = error rate
    among accepted at each coverage. Lower = better selective predictor."""
    s = np.asarray(scores, float)
    c = np.asarray(correct, float)
    order = np.argsort(-s, kind="mergesort")
    cum = np.cumsum(c[order])
    n = np.arange(1, len(c) + 1)
    return float(np.mean(1.0 - cum / n))


def bootstrap_ci(scores: list[float], labels: list[int], *,
                 metric: Callable[[list[float], list[int]], float] = auroc,
                 b: int = 4000, seed: int = 0,
                 alpha: float = 0.05) -> tuple[float, float, float]:
    """(point, ci_low, ci_high) for ``metric`` via paired bootstrap resampling.
    Skips degenerate resamples (single class). Percentile interval at ``alpha``."""
    rng = random.Random(seed)
    n = len(scores)
    vals: list[float] = []
    for _ in range(b):
        idx = [rng.randrange(n) for _ in range(n)]
        s = [scores[i] for i in idx]
        y = [labels[i] for i in idx]
        if 0 < sum(y) < len(y):
            v = metric(s, y)
            if not math.isnan(v):
                vals.append(v)
    vals.sort()
    point = metric(scores, labels)
    if not vals:
        return point, float("nan"), float("nan")
    lo = vals[int((alpha / 2) * len(vals))]
    hi = vals[min(len(vals) - 1, int((1 - alpha / 2) * len(vals)))]
    return point, lo, hi


def ece(probs: list[float], labels: list[int], *, n_bins: int = 10) -> float:
    """Expected calibration error. ``probs`` in [0,1] (divide 0-100 confidences by 100)."""
    p = np.asarray(probs, float)
    y = np.asarray(labels, float)
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    out = 0.0
    for i in range(n_bins):
        hi_inclusive = i == n_bins - 1
        m = (p >= bins[i]) & (p <= bins[i + 1] if hi_inclusive else p < bins[i + 1])
        if m.sum():
            out += m.mean() * abs(p[m].mean() - y[m].mean())
    return float(out)


def _phi(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _placements(x_pos: np.ndarray, x_neg: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
    """DeLong structural components: V10 over positives, V01 over negatives, and the AUC.
    S(a,b)=1 if a>b, 0.5 if tie, 0 else."""
    m, n = len(x_pos), len(x_neg)
    v10 = np.empty(m)
    for i in range(m):
        v10[i] = (np.sum(x_pos[i] > x_neg) + 0.5 * np.sum(x_pos[i] == x_neg)) / n
    v01 = np.empty(n)
    for j in range(n):
        v01[j] = (np.sum(x_pos > x_neg[j]) + 0.5 * np.sum(x_pos == x_neg[j])) / m
    return v10, v01, float(v10.mean())


def delong_test(scores_a: list[float], scores_b: list[float],
                labels: list[int]) -> dict[str, float]:
    """DeLong test for two CORRELATED AUCs (predictors A and B scored on the SAME samples).
    Returns {auc_a, auc_b, z, p} — p is two-sided for H0: AUC_A == AUC_B."""
    s_a = np.asarray(scores_a, float)
    s_b = np.asarray(scores_b, float)
    y = np.asarray(labels, int)
    pos = y == 1
    neg = y == 0
    m, n = int(pos.sum()), int(neg.sum())
    if m == 0 or n == 0:
        return {"auc_a": float("nan"), "auc_b": float("nan"), "z": float("nan"),
                "p": float("nan")}
    v10a, v01a, auc_a = _placements(s_a[pos], s_a[neg])
    v10b, v01b, auc_b = _placements(s_b[pos], s_b[neg])
    s10 = np.cov(np.vstack([v10a, v10b]))
    s01 = np.cov(np.vstack([v01a, v01b]))
    s = s10 / m + s01 / n
    var = float(s[0, 0] + s[1, 1] - 2 * s[0, 1])
    if var <= 0:
        z = 0.0 if abs(auc_a - auc_b) < 1e-12 else math.inf
    else:
        z = (auc_a - auc_b) / math.sqrt(var)
    p = 2.0 * (1.0 - _phi(abs(z))) if math.isfinite(z) else 0.0
    return {"auc_a": round(auc_a, 4), "auc_b": round(auc_b, 4),
            "z": round(z, 4) if math.isfinite(z) else z, "p": round(p, 4)}


__all__ = ["auroc", "aurc", "bootstrap_ci", "ece", "delong_test"]
