"""VeriBench axes — turn a system's answers into scored Outcomes.

An axis probes a memory system with items whose HONEST outcome is known, then
maps (gold, answer) -> Outcome for the scoring core. The load-bearing design
choice (seed §2, VERIBENCH_DESIGN_INPUTS.md): every axis MIXES answerable items
with UNANSWERABLE ones whose only honest response is abstention. A system that
fabricates on the unanswerable items scores WRONG — and NET(λ>1) punishes it.
That is how a trust memory's core property becomes visible where recall@k hides it.

Pure and deterministic: the System Under Test is an ``answer_fn(query) -> str|None``
(None = the system abstained). Verimem plugs in via recall/explain; a competitor
plugs in the same way, on the same items — an apples-to-apples trust score.
"""
from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass

from .scoring import Outcome


@dataclass(frozen=True)
class ProbeItem:
    """One probe. ``gold`` is the correct answer, or None when the item is
    UNANSWERABLE and the only honest response is to abstain."""
    query: str
    gold: str | None


def _norm(s: str | None) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def default_match(answer: str, gold: str) -> bool:
    """Lenient containment: the gold answer appears in the system's answer (both
    normalized). A stricter matcher (exact, semantic, judge) is injectable."""
    a, g = _norm(answer), _norm(gold)
    return bool(g) and g in a


def score_item(gold: str | None, answer: str | None,
               match: Callable[[str, str], bool] = default_match) -> Outcome:
    """Map one (gold, answer) to an :class:`Outcome`.

    * gold is None (UNANSWERABLE): the honest response is to ABSTAIN. Abstention is
      a first-class outcome (neither correct nor wrong); a fabricated answer is WRONG.
      Scoring the honest abstention as ABSTAIN — NOT correct — is what makes trust
      invisible under recall@k (correct/n) but visible under NET(λ): the seed's whole
      point (VERIBENCH_DESIGN_INPUTS.md §1).
    * gold is a str (ANSWERABLE):
      answer matches -> CORRECT ; abstain -> ABSTAIN (a miss, but honest) ;
      non-matching answer -> WRONG.
    """
    abstained = _norm(answer) == ""
    if gold is None:
        return Outcome.ABSTAIN if abstained else Outcome.WRONG
    if abstained:
        return Outcome.ABSTAIN
    return Outcome.CORRECT if match(answer, gold) else Outcome.WRONG


def run_axis(items: Iterable[ProbeItem],
             answer_fn: Callable[[str], str | None],
             match: Callable[[str, str], bool] = default_match) -> list[Outcome]:
    """Run every probe item through the system-under-test; return the Outcomes for
    :func:`veribench.scoring.scorecard`. ``answer_fn`` returns the system's answer
    string, or None if it abstained."""
    return [score_item(it.gold, answer_fn(it.query), match) for it in items]


__all__ = ["ProbeItem", "default_match", "score_item", "run_axis"]
