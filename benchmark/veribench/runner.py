"""VeriBench runner — wire a system to the axes, produce a scorecard.

``run_bench(items, answer_fn)`` runs an axis and returns the full scorecard (counts,
coverage, NET across the λ-sweep, crossover-λ). ``make_verimem_answer_fn(mem)`` adapts
a Verimem ``Memory`` to the ``answer_fn`` contract:

    recall the top fact; return its text if the store surfaced one ABOVE its own
    noise floor, else None (the store abstained).

The floor IS the trust signal: an unanswerable query returns nothing above it, so the
honest system abstains and scores CORRECT on the unanswerable items — exactly the
behavior NET(λ>1) rewards. A competitor with no floor keeps returning its nearest
(irrelevant) neighbor and scores WRONG on the same items. Same probe set, same
scorecard, apples-to-apples.

Pure orchestration — the model only loads if you actually pass a real ``Memory``;
tests inject a fake store, so the runner itself stays hermetic.
"""
from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from .axes import ProbeItem, default_match, run_axis
from .scoring import scorecard


def make_verimem_answer_fn(mem: Any, *, k: int = 1,
                           min_score: float | None = None) -> Callable[[str], str | None]:
    """Adapt a Verimem ``Memory`` (anything with ``search(query, k) -> [hit,...]``)
    to the axis ``answer_fn``: top hit's text, or None when the store surfaced
    nothing (or nothing above ``min_score``) — i.e. it abstained.

    ``min_score`` (optional) is an explicit floor on the top hit's cosine; leave
    None to trust the store's own empty-result as the abstention signal.
    """
    def answer_fn(query: str) -> str | None:
        hits = mem.search(query, k=k) or []
        if not hits:
            return None
        top = hits[0]
        if min_score is not None and float(top.get("score", 1.0)) < min_score:
            return None
        return top.get("text") or top.get("proposition") or None
    return answer_fn


def run_bench(items: Iterable[ProbeItem],
              answer_fn: Callable[[str], str | None],
              *, match: Callable[[str, str], bool] = default_match) -> dict:
    """Run ``items`` through ``answer_fn`` and return the VeriBench scorecard."""
    return scorecard(run_axis(items, answer_fn, match))


__all__ = ["make_verimem_answer_fn", "run_bench"]
