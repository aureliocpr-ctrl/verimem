"""hallucination-rate@k — la metrica del fossato anti-confabulazione.

The competitive number no cosine-only store can report. Mem0/Zep retrieve facts
with NO reliability signal, so every returned fact is "to be verified" by
construction — their hallucination-rate@k is ~1.0. Engram attaches a live
``trust_signal`` to each hit (``trusted | stale | contested | obsolete |
unverified``); this metric measures the fraction of the top-k whose verdict is
*unreliable* — the hallucination risk the recall hands to the caller.

Definitions
-----------
* ``RISKY = {obsolete, contested, unverified}`` — the fact is retracted,
  contradicted, or never verified; trusting it propagates error.
* ``stale`` is grey (old but not retracted) and is reported SEPARATELY as
  ``stale_rate@k`` rather than folded into the hallucination figure.
* Per-query rate = ``#risky_in_topk / #hits``; the headline is the macro
  average over queries that returned at least one hit (a no-hit query exposes
  no risk and has no denominator, so it is excluded from the mean and counted
  in ``n_queries_no_hits``). ``hallucination_rate_micro`` is the pooled
  ``total_risky / total_hits`` for callers who prefer the micro average.

Pure: the only dependency is ``SemanticMemory.recall(trust_signals=True)``.
"""
from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .semantic import SemanticMemory

# Verdicts that count as hallucination risk. Kept as a module constant so a
# test can contract-lock it and callers can introspect it.
_RISKY_VERDICTS = frozenset({"obsolete", "contested", "unverified"})

# Every verdict compute_trust_signal can emit — used to seed the breakdown so
# the shape is stable regardless of which verdicts actually occur.
_ALL_VERDICTS = ("trusted", "stale", "contested", "obsolete", "unverified")


def rate_from_verdicts(verdicts: list[str]) -> tuple[float, float]:
    """Pure core: ``(risky_rate, stale_rate)`` for ONE query's hit verdicts.

    Empty input → ``(0.0, 0.0)`` (no hits expose no risk).
    """
    n = len(verdicts)
    if n == 0:
        return 0.0, 0.0
    risky = sum(1 for v in verdicts if v in _RISKY_VERDICTS)
    stale = sum(1 for v in verdicts if v == "stale")
    return risky / n, stale / n


def hallucination_rate_at_k(
    sm: SemanticMemory,
    queries: Iterable[str],
    k: int = 5,
) -> dict[str, Any]:
    """Measure hallucination-rate@k over ``queries`` against ``sm``.

    For each non-empty query, runs ``sm.recall(q, k, trust_signals=True)`` and
    tallies the top-k verdicts. Returns the macro hallucination/stale rates, the
    micro hallucination rate, and the full verdict breakdown.

    The recall path is whatever the live config dictates (fusion, rerank,
    filters); this metric observes its OUTPUT, it does not change it. Empty /
    whitespace queries are skipped.
    """
    qs = [q for q in queries if (q or "").strip()]
    breakdown: dict[str, int] = {v: 0 for v in _ALL_VERDICTS}
    risky_rate_sum = 0.0
    stale_rate_sum = 0.0
    n_with_hits = 0
    n_no_hits = 0
    total_hits = 0
    total_risky = 0

    for q in qs:
        hits = sm.recall(q, k=k, trust_signals=True)
        if not hits:
            n_no_hits += 1
            continue
        n_with_hits += 1
        verdicts: list[str] = []
        for tup in hits:
            # trust_signals=True → 3-tuple (Fact, sim, TrustSignal); be
            # defensive if a caller passed a 2-tuple recall result by mistake.
            sig = tup[2] if len(tup) >= 3 else None
            verdict = getattr(sig, "verdict", "unverified")
            verdicts.append(verdict)
            breakdown[verdict] = breakdown.get(verdict, 0) + 1
        risky_rate, stale_rate = rate_from_verdicts(verdicts)
        risky_rate_sum += risky_rate
        stale_rate_sum += stale_rate
        total_hits += len(verdicts)
        total_risky += sum(1 for v in verdicts if v in _RISKY_VERDICTS)

    macro = (risky_rate_sum / n_with_hits) if n_with_hits else 0.0
    stale_macro = (stale_rate_sum / n_with_hits) if n_with_hits else 0.0
    micro = (total_risky / total_hits) if total_hits else 0.0
    # Metric-honesty (3-round audit, fix-order-meta #0): a recall BLACKOUT — real
    # queries but ZERO hits across all of them — must NOT report 0.0 (a perfect
    # score). The anti-confab metric would lie exactly when recall is broken. Emit
    # None for the rates + degraded=True + coverage, so the caller distinguishes
    # "0 risk over real hits" from "no recall happened". Zero queries (nothing to
    # measure) is NOT a blackout and is not flagged degraded.
    blackout = len(qs) > 0 and n_with_hits == 0
    return {
        "hallucination_rate_at_k": None if blackout else round(macro, 4),
        "stale_rate_at_k": None if blackout else round(stale_macro, 4),
        "hallucination_rate_micro": None if blackout else round(micro, 4),
        "coverage": round(n_with_hits / len(qs), 4) if qs else 0.0,
        "degraded": blackout,
        "k": k,
        "n_queries": len(qs),
        "n_queries_with_hits": n_with_hits,
        "n_queries_no_hits": n_no_hits,
        "total_hits": total_hits,
        "verdict_breakdown": breakdown,
    }


__all__ = ["hallucination_rate_at_k", "rate_from_verdicts", "_RISKY_VERDICTS"]
