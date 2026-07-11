"""VeriBench scoring — the scoring function IS the benchmark.

Seed decision (docs/VERIBENCH_DESIGN_INPUTS.md §1, from the Vivarium
causal-abstention result): recall@k-style **symmetric** scoring makes a trust
memory's core property — knowing when it doesn't know — **invisible**. Every
existing memory benchmark scores symmetrically; that is exactly why the market
"can't see" trust.

VeriBench scores **NET = (correct − λ·wrong) / n** with a DECLARED λ ≥ 1 (a wrong
answer costs more than an honest silence), reported across a λ-sweep, plus
coverage. Abstention ("I don't know") is a first-class outcome, NOT a miss.

Pure, deterministic, no model / no network. The axis probes that turn a store's
answers into `Outcome`s plug in on top; this is the load-bearing core they all
report through.
"""
from __future__ import annotations

from collections.abc import Iterable
from enum import Enum


class Outcome(str, Enum):
    """The three ways a trust memory can answer a probe."""
    CORRECT = "correct"
    WRONG = "wrong"
    ABSTAIN = "abstain"   # honest "I don't know" — NOT a miss


#: Declared λ-sweep. λ=1 is symmetric (trust invisible); λ>1 rewards abstaining
#: over guessing wrong — the regime where a trust memory earns its keep.
DEFAULT_LAMBDAS: tuple[float, ...] = (1.0, 2.0, 5.0, 10.0)


def _tally(outcomes: Iterable[Outcome]) -> tuple[int, int, int, int]:
    c = w = a = 0
    for o in outcomes:
        if o == Outcome.CORRECT:
            c += 1
        elif o == Outcome.WRONG:
            w += 1
        elif o == Outcome.ABSTAIN:
            a += 1
        else:  # defensive: unknown outcome is not silently a pass
            raise ValueError(f"not an Outcome: {o!r}")
    return c, w, a, c + w + a


def net_score(outcomes: Iterable[Outcome], lam: float) -> float:
    """NET = (correct − λ·wrong) / n. ``lam`` (λ) is the cost of a WRONG answer
    relative to an abstention. n counts abstentions in the denominator (silence
    is a choice, not a free pass). Empty set → 0.0."""
    if lam < 0:
        raise ValueError("lambda must be >= 0")
    c, w, _a, n = _tally(outcomes)
    return (c - lam * w) / n if n else 0.0


def coverage(outcomes: Iterable[Outcome]) -> float:
    """Fraction that produced an ANSWER (correct or wrong) — i.e. did not abstain.
    Trust has a cost: high coverage with low net means the store guesses."""
    c, w, _a, n = _tally(outcomes)
    return (c + w) / n if n else 0.0


def counts(outcomes: Iterable[Outcome]) -> dict[str, int]:
    c, w, a, n = _tally(outcomes)
    return {"n": n, "correct": c, "wrong": w, "abstain": a}


def crossover_lambda(outcomes: Iterable[Outcome]) -> float | None:
    """λ* = correct / wrong: the cost-of-wrong at which NET crosses zero for this
    set (below λ* net>0, above net<0). None when there are no wrong answers — the
    system never goes net-negative, however high the stakes (pure honesty). Makes
    the Vivarium abstention crossover an explicit, per-system number."""
    c, w, _a, _n = _tally(outcomes)
    return c / w if w else None


def scorecard(outcomes: Iterable[Outcome],
              lambdas: Iterable[float] = DEFAULT_LAMBDAS) -> dict:
    """Full VeriBench scorecard: counts, coverage, NET across the declared λ-sweep,
    and the crossover λ.

    The λ-sweep is the whole point: a single symmetric (λ=1) number hides what a
    trust memory does. Watching NET as λ rises separates a system that **abstains
    honestly** (net decays slowly) from one that **fabricates** (net collapses) —
    even when both have identical coverage or identical λ=1 scores.
    """
    outcomes = list(outcomes)
    xover = crossover_lambda(outcomes)
    return {
        **counts(outcomes),
        "coverage": round(coverage(outcomes), 4),
        "net": {f"lambda_{lam:g}": round(net_score(outcomes, lam), 4)
                for lam in lambdas},
        "crossover_lambda": round(xover, 4) if xover is not None else None,
    }


__all__ = [
    "Outcome", "DEFAULT_LAMBDAS", "net_score", "coverage", "counts",
    "crossover_lambda", "scorecard",
]
