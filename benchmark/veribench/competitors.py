"""VeriBench competitor adapters — plug a competitor into the axis ``answer_fn``.

Why put a competitor on the SAME axes: on the ANSWERABLE items it retrieves like
anyone (parity — that is honest); on the UNANSWERABLE items it keeps returning its
nearest neighbor because it has NO abstention floor, so it cannot say "I don't
know" — and scores WRONG exactly where Verimem abstains. NET(λ) turns that into a
visible gap. This is not a recall contest; it is a trust contest, on axes the
competitor does not have.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any


def make_mem0_answer_fn(mem0_store: Any, *,
                        min_score: float | None = None) -> Callable[[str], str | None]:
    """Adapt a mem0 ``Memory`` (``search(query) -> {"results": [{"memory", "score"}]}``
    — or a bare list) to the axis ``answer_fn``.

    mem0 has no abstention floor: by default it returns its nearest memory for ANY
    query, including unanswerable ones, so ``answer_fn`` (almost) never returns None
    — which is precisely what the abstention axis exposes. ``min_score`` lets an
    operator bolt an explicit floor on (the charitable configuration); without it we
    measure mem0 as shipped.
    """
    def answer_fn(query: str) -> str | None:
        res = mem0_store.search(query)
        results = res.get("results", res) if isinstance(res, dict) else res
        if not results:
            return None
        top = results[0]
        if min_score is not None and float(top.get("score", 1.0)) < min_score:
            return None
        return top.get("memory") or top.get("text") or None
    return answer_fn


__all__ = ["make_mem0_answer_fn"]
