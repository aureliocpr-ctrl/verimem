"""Selective-prediction deployment metrics at DECLARED operating points.

Why (Oxford 2603.21172, via the cortex research bridge 2026-07-14): a strong
AUROC says the confidence scores DISCRIMINATE answerable from unanswerable; it
does NOT say the system OPERATES at the declared risk when the operator sets
the SLA knob λ (`engram/sla.py`: answer iff confidence > λ/(1+λ)). sla.py
itself declares the gap — mapping a raw relevance score to a calibrated
P(correct) "is a separate, validated wiring step, NOT asserted here". These
metrics measure exactly that step:

  * ``selective_risk_coverage`` — risk among answered / fraction answered at a
    threshold (strict >, same side as ``sla.should_answer``);
  * ``aurc`` / ``e_aurc`` — area under the risk-coverage curve and its EXCESS
    over the oracle ranking (0 = the scores order errors perfectly).
    Tie-conservative: within a confidence tie the WRONG answers rank first, so
    the number never flatters the store;
  * ``tce_at_lambda`` — at the λ operating point: |observed selective risk −
    risk the confidences THEMSELVES promise| (calibration at the operating
    point), plus the SLA gap vs the declared target 1/(1+λ) and whether the
    point is even OPERABLE (zero coverage is declared, never scored);
  * ``isotonic_fit`` — pure PAV score→P(correct) calibration; fit on a dev
    split, applied held-out (the discipline: the fixer never reads the eval).

A record is ``(confidence, correct)`` where ``correct`` answers "IF the system
answers this query, is the answer right?" — for an unanswerable query that is
False by construction. Pure logic, no I/O, no store dependency.
"""
from __future__ import annotations

from bisect import bisect_left
from typing import Any, Callable, Iterable

__all__ = ["aurc", "e_aurc", "isotonic_fit", "selective_risk_coverage",
           "tce_at_lambda"]

Record = tuple[float, bool]


def _clean(records: Iterable[Record]) -> list[Record]:
    return [(float(c), bool(ok)) for c, ok in records]


def selective_risk_coverage(records: Iterable[Record], *,
                            threshold: float) -> tuple[float | None, float]:
    """(risk among answered, coverage) at ``threshold`` — strict ``>`` like
    ``sla.should_answer``. Zero coverage → risk None (undefined, not 0)."""
    rs = _clean(records)
    if not rs:
        return None, 0.0
    answered = [ok for c, ok in rs if c > threshold]
    coverage = len(answered) / len(rs)
    if not answered:
        return None, 0.0
    risk = sum(1 for ok in answered if not ok) / len(answered)
    return risk, coverage


def aurc(records: Iterable[Record]) -> float:
    """Area under the risk-coverage curve: rank by confidence (desc), take the
    mean of the cumulative risk after each answered item. Within a confidence
    TIE the wrong answers rank FIRST (worst case), so ties never flatter.

    Relation to ``benchmark/stats.aurc(scores, correct)`` (the numpy one used
    by older benches): same definition, different API and TIE RULE — stats.py
    keeps input order within ties (mergesort), this one is deliberately
    worst-case. On tie-free inputs the two agree exactly (pinned by
    ``test_agrees_with_benchmark_stats_aurc_on_tie_free_input``)."""
    rs = _clean(records)
    if not rs:
        return 0.0
    ranked = sorted(rs, key=lambda r: (-r[0], r[1]))   # False < True: wrong first
    total = wrong = 0.0
    acc = 0.0
    for i, (_c, ok) in enumerate(ranked, start=1):
        wrong += 0.0 if ok else 1.0
        acc += wrong / i
        total += 1
    return acc / total


def e_aurc(records: Iterable[Record]) -> float:
    """Excess AURC over the ORACLE ranking (all correct first): 0 = the scores
    already order the errors perfectly; the gap is what better confidence
    estimation could still buy."""
    rs = _clean(records)
    if not rs:
        return 0.0
    n_wrong = sum(1 for _c, ok in rs if not ok)
    oracle = [(1.0, True)] * (len(rs) - n_wrong) + [(0.0, False)] * n_wrong
    return aurc(rs) - aurc(oracle)


def tce_at_lambda(records: Iterable[Record], lam: float) -> dict[str, Any]:
    """Calibration at the DECLARED operating point λ (threshold λ/(1+λ)):

      * ``expected_risk``  — 1 − mean(confidence of the answered): the risk the
        confidences themselves promise at this point;
      * ``observed_risk``  — the risk actually delivered;
      * ``tce``            — |observed − expected|: 0 means the knob does what
        it says on the box;
      * ``sla_target_risk``— 1/(1+λ), the break-even the operator declared;
        ``sla_gap`` = observed − target (negative = inside SLA), ``sla_met``;
      * zero coverage → observed/tce/sla_met are None: the operating point is
        INOPERABLE with these scores — declared, never scored as a pass."""
    lam = float(lam)
    threshold = lam / (1.0 + lam)
    rs = _clean(records)
    answered = [(c, ok) for c, ok in rs if c > threshold]
    coverage = (len(answered) / len(rs)) if rs else 0.0
    out: dict[str, Any] = {
        "lam": lam, "threshold": threshold, "coverage": coverage,
        "n": len(rs), "n_answered": len(answered),
        "sla_target_risk": 1.0 / (1.0 + lam),
    }
    if not answered:
        out.update({"observed_risk": None, "expected_risk": None,
                    "tce": None, "sla_gap": None, "sla_met": None})
        return out
    observed = sum(1 for _c, ok in answered if not ok) / len(answered)
    expected = 1.0 - (sum(c for c, _ok in answered) / len(answered))
    out.update({
        "observed_risk": observed,
        "expected_risk": expected,
        "tce": abs(observed - expected),
        "sla_gap": observed - out["sla_target_risk"],
        "sla_met": observed <= out["sla_target_risk"],
    })
    return out


def isotonic_fit(pairs: Iterable[Record]) -> Callable[[float], float]:
    """Pure PAV (pool-adjacent-violators) isotonic regression of correctness on
    score. Returns a monotone step function score→P(correct). Fit on DEV pairs
    only; apply held-out. No dependencies; deterministic."""
    pts = sorted(_clean(pairs))
    if not pts:
        return lambda _x: 0.5      # no evidence -> neutral prior, declared
    # blocks: [sum_y, n, max_score]
    blocks: list[list[float]] = []
    for score, ok in pts:
        blocks.append([1.0 if ok else 0.0, 1.0, score])
        while len(blocks) > 1 and (blocks[-2][0] / blocks[-2][1]
                                   >= blocks[-1][0] / blocks[-1][1]):
            y2, n2, s2 = blocks.pop()
            blocks[-1][0] += y2
            blocks[-1][1] += n2
            blocks[-1][2] = s2
        # merge uses >= so equal means collapse too (canonical minimal form)
    bounds = [b[2] for b in blocks]
    means = [b[0] / b[1] for b in blocks]

    def predict(x: float) -> float:
        i = bisect_left(bounds, float(x))
        return means[min(i, len(means) - 1)]

    return predict
