"""Error-cost → abstention SLA: one number, the same meaning end to end.

The operator declares how much a WRONG answer costs relative to an ABSTENTION
(silence). That number is λ — and it is the SAME λ VeriBench scores NET at
(``benchmark/veribench/scoring.py``): the benchmark measures the store at λ, the
operator TUNES the store at λ. Legal/medical deployments set λ high (a wrong
answer is expensive → abstain unless quite sure); a brainstorming assistant sets
λ low (silence is the expensive outcome → answer more).

Decision theory (why the threshold is exactly λ/(1+λ), not a hand-picked floor):
answering a candidate whose probability of being correct is ``p`` earns +1 when
right and −λ when wrong; abstaining earns 0. So answer iff

    p·(+1) + (1−p)·(−λ) > 0   ⇔   p > λ/(1+λ).

λ=1 (symmetric) → 0.5; λ=5 → 0.833; λ=10 → 0.909; λ<1 (silence costs more) → below
0.5 (answer more). This is also the NET(λ) break-even accuracy: a store that
answers with accuracy ``a`` on its answered items nets positive iff a > λ/(1+λ) —
so tuning the store to this threshold is exactly maximising its VeriBench NET.

This module is the pure decision rule + the env knob. Mapping a raw relevance
score to a calibrated P(correct) (so the LIVE read-path can apply
``should_answer`` on real hits) needs a calibration curve and is a separate,
validated wiring step — NOT asserted here.
"""
from __future__ import annotations

import os

__all__ = ["error_cost", "answer_threshold", "should_answer"]

_DEFAULT_LAMBDA = 1.0


def error_cost() -> float:
    """``ENGRAM_ERROR_COST`` = λ, the cost of a wrong answer in units of one
    abstention. Default 1.0 (symmetric — the current, un-tuned behavior). A
    non-positive or unparseable value falls back to 1.0 (fail-safe: never a
    zero/negative threshold that would answer everything)."""
    try:
        lam = float(os.environ.get("ENGRAM_ERROR_COST", "1"))
    except ValueError:
        return _DEFAULT_LAMBDA
    return lam if lam > 0 else _DEFAULT_LAMBDA


def answer_threshold(lam: float | None = None) -> float:
    """Confidence threshold to answer vs abstain: ``λ/(1+λ)``. The decision-
    theoretic optimum AND the VeriBench NET(λ) break-even accuracy — one number,
    the same meaning end to end. ``lam=None`` reads the ``ENGRAM_ERROR_COST`` knob."""
    lam = error_cost() if lam is None else float(lam)
    if lam <= 0:
        return 0.0
    return lam / (1.0 + lam)


def should_answer(confidence: float, lam: float | None = None) -> bool:
    """Answer iff estimated P(correct) STRICTLY exceeds the SLA threshold, else
    abstain. Strict so that a confidence sitting exactly on the break-even (where
    answering and abstaining have equal expected value) takes the safe side."""
    return float(confidence) > answer_threshold(lam)
