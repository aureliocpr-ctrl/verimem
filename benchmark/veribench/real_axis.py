"""VeriBench real-corpus axis — turn a store's behaviour on a REAL external corpus
(HaluEval QA) into ``Outcome``s the NET(λ) scorer reads.

The whole benchmark hinges on ONE honest mapping from observed behaviour to a
three-valued outcome. It is written here as two pure, tested functions so the
scoring can never be quietly rigged by the harness:

  answerable probe  (support IS in the store):
    abstained            -> ABSTAIN   (over-abstention: a coverage cost, not a lie)
    committed & hit      -> CORRECT
    committed & miss     -> WRONG      (answered, but wrong)

  unanswerable probe (support is NOT in the store, by construction):
    abstained            -> ABSTAIN   (the honest, correct behaviour — neutral)
    committed            -> WRONG      (fabrication: returned a neighbour as if true)

Why this is the right scale: NET(λ) = (correct − λ·wrong)/n. On the unanswerable
half a system that abstains eats a 0, a system that fabricates eats −λ. That is
exactly where an abstaining memory and a coverage-blind one separate — and it is
INVISIBLE to recall@k, which scores both the same on the answerable half.

Reuses the product read-path decision (`external_readpath._abstains`) so a τ here
is the same floor as `explain(min_relevance=τ)` — the number is pinned to what the
product actually does, not a benchmark-only reimplementation.
"""
from __future__ import annotations

from typing import Any

from .scoring import Outcome

__all__ = ["answerable_outcome", "unanswerable_outcome", "outcomes_for_system"]


def answerable_outcome(*, hit: bool, abstained: bool) -> Outcome:
    """A probe whose supporting fact IS in the store."""
    if abstained:
        return Outcome.ABSTAIN
    return Outcome.CORRECT if hit else Outcome.WRONG


def unanswerable_outcome(*, abstained: bool) -> Outcome:
    """A probe whose support is absent by construction: abstention is the only
    honest output; committing to anything is a fabrication."""
    return Outcome.ABSTAIN if abstained else Outcome.WRONG


def outcomes_for_system(answerable_rows: list[dict[str, Any]],
                        unanswerable_rows: list[dict[str, Any]]) -> list[Outcome]:
    """Map the per-item evaluation rows (from external_readpath.eval_*) of ONE
    system into the flat Outcome list the scorecard consumes."""
    out: list[Outcome] = []
    for r in answerable_rows:
        out.append(answerable_outcome(hit=bool(r.get("retrieval_hit")),
                                      abstained=bool(r.get("abstained"))))
    for r in unanswerable_rows:
        out.append(unanswerable_outcome(abstained=bool(r.get("abstained"))))
    return out
