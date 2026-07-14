"""Guardian at the read-path — ACCEPT / CORRECT / ABSTAIN (cortex transfer).

The cortex lab measured the pattern (guardian.correct: 0 false answers over
2000 queries, accuracy 0.507→0.844 on its rule world): when the store CONTAINS
a better-guaranteed truth, don't just block the wrong candidate — SERVE the
truth, with both sides cited. This is the product incarnation on copula facts:

  * ACCEPT   — the top hit stands (no rival on the same subject);
  * CORRECT  — a rival fact about the SAME subject carries a strictly better
               epistemic guarantee (proven > unbeaten > unlabeled; refuted is
               disqualified outright) → answer with the winner, cite both;
  * ABSTAIN  — a real conflict with no epistemic winner (never pick silently:
               the conflict is shown), or no support at all.

Scope, honest: subject matching is the composer's copula parse — the same
world-bound v1 as composition (no copula structure → the guardian simply
ACCEPTs like today's read-path). Refuted facts are never served, even when
recall ranks them first.
"""
from __future__ import annotations

from typing import Any

from .composer import _copula_parse

__all__ = ["correct_read"]

_RANK = {"refuted": -1, None: 0, "unbeaten": 1, "proven": 2}


def _rank(fact: Any) -> int:
    label = getattr(fact, "epistemic", None) or None
    return _RANK[label["kind"]] if label else 0


def correct_read(mem: Any, query: str, *, k: int = 5) -> dict[str, Any]:
    """One gated read with correction. Returns
    ``{verdict, answer, served_id, evidence, reason}``."""
    hits = mem.search(query, k=k)
    if not hits:
        return {"verdict": "ABSTAIN", "answer": None, "served_id": None,
                "evidence": [], "reason": "no_support"}
    facts = [f for f in (mem.semantic.get(h.get("id", "")) for h in hits) if f]
    # group the copula facts by subject; non-copula hits pass through untouched
    contenders: dict[str, list[Any]] = {}
    for f in facts:
        parsed = _copula_parse(f.proposition)
        if parsed:
            contenders.setdefault(parsed[0], []).append(f)

    top = facts[0]
    top_parsed = _copula_parse(top.proposition)
    rivals = contenders.get(top_parsed[0], [top]) if top_parsed else [top]
    # a refuted fact never gets served — drop it from contention entirely
    live = [f for f in rivals if _rank(f) >= 0] or []
    if not live:
        return {"verdict": "ABSTAIN", "answer": None, "served_id": None,
                "evidence": [f.id for f in rivals], "reason": "all_refuted"}

    values = {(_copula_parse(f.proposition) or ("", "", ""))[1] for f in live}
    if len(values) <= 1:                     # agreement (or single voice)
        winner = max(live, key=_rank)
        return {"verdict": "ACCEPT", "answer": winner.proposition,
                "served_id": winner.id, "evidence": [f.id for f in rivals],
                "reason": "unchallenged"}

    best = max(live, key=_rank)
    others = [f for f in live if f is not best]
    if all(_rank(best) > _rank(f) for f in others):
        # CORRECT whenever a real conflict was resolved by the label — never
        # dependent on which side recall happened to rank first (that order is
        # not deterministic w.r.t. content, the verdict must be).
        label = (best.epistemic or {}).get("kind", "unlabeled")
        return {"verdict": "CORRECT", "answer": best.proposition,
                "served_id": best.id, "evidence": [f.id for f in rivals],
                "reason": f"conflict resolved by epistemic rank: {label} wins"}
    # a tie between conflicting guarantees is a REAL conflict — show, don't pick
    return {"verdict": "ABSTAIN", "answer": None, "served_id": None,
            "evidence": [f.id for f in live],
            "reason": "conflict_without_epistemic_winner"}
