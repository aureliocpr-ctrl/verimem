"""R&D 2026-06-16 — trust-signal calibration harness.

Measures whether the categorical trust-signal is CALIBRATED: when it implies a
fact is reliable, is it? The ground-truth `reliable` flag comes from the SIMULATED
WORLD, NOT from the fact properties the signal reads — otherwise the test is a
tautology.

The dial that matters: `unobserved_p`, the fraction of facts that became obsolete
in the world but whose supersession Engram never recorded (an external
knowledge-update the memory didn't witness). At unobserved_p=0 the signal has
full information; at 1.0 it is blind to every change. The Brier-vs-p curve shows
that the signal is calibrated only as far as its observation is complete — which
is exactly the argument for a truth-reconciliation loop.

Composition (declared, fixed):
  40% current true & verified        -> reliable=1
  20% obsolete in the world          -> reliable=0  (observed w.p. 1-unobserved_p)
  15% contested (contradiction)      -> reliable=0  (contradiction recorded)
  15% old (>180d) but still true     -> reliable=1
  10% low-conf model_claim           -> reliable=1 for half, 0 for half
"""
from __future__ import annotations

import random
from dataclasses import dataclass

from engram.semantic import Fact
from engram.trust_calibration import (
    brier_score,
    expected_calibration_error,
    reliability_table,
)
from engram.trust_signal import compute_trust_signal

# The implied P(reliable) for each categorical verdict. This mapping is itself
# the hypothesis the harness calibrates — it is monotone in concern.
VERDICT_TO_PROB = {
    "trusted": 0.90,
    "stale": 0.50,
    "unverified": 0.40,
    "contested": 0.20,
    "obsolete": 0.05,
}

_DAY = 86400.0


@dataclass(frozen=True)
class CalibrationResult:
    n: int
    brier: float
    ece: float
    over_trust_rate: float       # frac of reliable=0 facts the signal implied >=0.7
    over_caution_rate: float     # frac of reliable=1 facts the signal implied <=0.5
    verdict_counts: dict
    reliability: list


def make_calibration_dataset(
    n: int, *, unobserved_p: float, now: float, seed: int = 0,
) -> list[tuple[Fact, int, str | None]]:
    """Return ``[(fact, reliable, contradiction_partner_id|None), ...]``."""
    rng = random.Random(seed)
    out: list[tuple[Fact, int, str | None]] = []
    for i in range(n):
        r = i / n  # deterministic stratification
        fid = f"cal{i:05d}"
        if r < 0.40:  # current, true, verified
            f = Fact(id=fid, proposition=f"fact {i} current truth", topic="t",
                     status="verified", confidence=0.9,
                     created_at=now - rng.uniform(1, 60) * _DAY)
            out.append((f, 1, None))
        elif r < 0.60:  # obsolete in the world
            observed = rng.random() >= unobserved_p
            f = Fact(id=fid, proposition=f"fact {i} stale config value", topic="t",
                     status="verified", confidence=0.8,
                     created_at=now - rng.uniform(10, 120) * _DAY,
                     superseded_by=(f"succ{i}" if observed else None),
                     superseded_reason=("value changed" if observed else ""))
            out.append((f, 0, None))
        elif r < 0.75:  # contested (a contradiction is recorded)
            f = Fact(id=fid, proposition=f"fact {i} disputed claim", topic="t",
                     status="verified", confidence=0.7,
                     created_at=now - rng.uniform(1, 90) * _DAY)
            out.append((f, 0, f"contra{i}"))
        elif r < 0.90:  # old but still true (stable fact)
            f = Fact(id=fid, proposition=f"fact {i} stable old truth", topic="t",
                     status="verified", confidence=0.85,
                     created_at=now - rng.uniform(200, 400) * _DAY)
            out.append((f, 1, None))
        else:  # low-confidence model_claim, half true half false
            reliable = i % 2
            f = Fact(id=fid, proposition=f"fact {i} model guess", topic="t",
                     status="model_claim", confidence=0.3,
                     created_at=now - rng.uniform(1, 30) * _DAY)
            out.append((f, reliable, None))
    return out


def evaluate_calibration(
    dataset, *, now: float, contradiction_store, sm, n_bins: int = 10,
    scorer=None,
) -> CalibrationResult:
    """Score each fact's implied P(reliable) and measure calibration.

    Default scorer = the categorical trust-signal mapped via VERDICT_TO_PROB.
    Pass ``scorer(fact) -> float`` to evaluate an alternative (e.g. a continuous
    trust score) on the SAME dataset and ground-truth, for a fair comparison.
    """
    probs: list[float] = []
    outcomes: list[int] = []
    counts: dict = {}
    over_trust = 0
    n_unreliable = 0
    over_caution = 0
    n_reliable = 0
    for fact, reliable, _ in dataset:
        if scorer is None:
            ts = compute_trust_signal(
                fact, sm, now=now, contradiction_store=contradiction_store)
            p = VERDICT_TO_PROB[ts.verdict]
            counts[ts.verdict] = counts.get(ts.verdict, 0) + 1
        else:
            p = float(scorer(fact))
        probs.append(p)
        outcomes.append(int(reliable))
        if reliable == 0:
            n_unreliable += 1
            if p >= 0.70:
                over_trust += 1
        else:
            n_reliable += 1
            if p <= 0.50:
                over_caution += 1
    return CalibrationResult(
        n=len(dataset),
        brier=brier_score(probs, outcomes),
        ece=expected_calibration_error(probs, outcomes, n_bins=n_bins),
        over_trust_rate=(over_trust / n_unreliable) if n_unreliable else 0.0,
        over_caution_rate=(over_caution / n_reliable) if n_reliable else 0.0,
        verdict_counts=counts,
        reliability=reliability_table(probs, outcomes, n_bins=n_bins),
    )


def register_contradictions(dataset, contradiction_store) -> None:
    """Record a contradiction for every dataset fact flagged contested, so the
    trust-signal's contested path actually fires at evaluation time."""
    from engram.contradiction import Contradiction
    for fact, _, partner in dataset:
        if partner is not None:
            contradiction_store.add(Contradiction(
                fact_a_id=fact.id, fact_b_id=partner,
                kind="negation", similarity=0.9))


__all__ = [
    "VERDICT_TO_PROB",
    "CalibrationResult",
    "make_calibration_dataset",
    "evaluate_calibration",
    "register_contradictions",
]
