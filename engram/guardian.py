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

user_belief awareness (Giro 2 §3.4): the guardian is the ONE reader that opts
into beliefs (``include_beliefs=True``), because its job is to correct them —
an unverified USER assertion participates in conflict DETECTION but can never
WIN: a corroborated rival is served with the belief cited as ``uncorroborated``
("previously asserted, not corroborated"); a subject supported ONLY by beliefs
is an ABSTAIN, never an answer. Every verdict carries an ``uncorroborated``
list (empty when none) so callers get a stable schema.
"""
from __future__ import annotations

from typing import Any

from .composer import _copula_parse

__all__ = ["correct_read"]

_RANK = {"refuted": -1, None: 0, "unbeaten": 1, "proven": 2}


def _rank(fact: Any) -> int:
    label = getattr(fact, "epistemic", None) or None
    return _RANK[label["kind"]] if label else 0


def _is_belief(fact: Any) -> bool:
    return getattr(fact, "status", "") == "user_belief"


def _value(fact: Any) -> str:
    return (_copula_parse(fact.proposition) or ("", "", ""))[1]


def correct_read(mem: Any, query: str, *, k: int = 5) -> dict[str, Any]:
    """One gated read with correction. Returns
    ``{verdict, answer, served_id, evidence, uncorroborated, reason}``."""
    hits = mem.search(query, k=k, include_beliefs=True)
    if not hits:
        return {"verdict": "ABSTAIN", "answer": None, "served_id": None,
                "evidence": [], "uncorroborated": [], "reason": "no_support"}
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
                "evidence": [f.id for f in rivals], "uncorroborated": [],
                "reason": "all_refuted"}

    # beliefs detect conflicts but never win; a beliefs-only subject abstains
    beliefs = [f for f in live if _is_belief(f)]
    servable = [f for f in live if not _is_belief(f)]
    if not servable:
        return {"verdict": "ABSTAIN", "answer": None, "served_id": None,
                "evidence": [f.id for f in rivals],
                "uncorroborated": [f.id for f in beliefs],
                "reason": "only_unverified_user_assertion"}

    values = {_value(f) for f in servable}
    if len(values) <= 1:                     # agreement (or single voice)
        winner = max(servable, key=_rank)
        overridden = [f for f in beliefs if _value(f) != _value(winner)]
        if overridden:
            # the sycophancy correction: the user asserted X, the store holds
            # a corroborated Y — serve Y, cite X as previously-asserted.
            return {"verdict": "CORRECT", "answer": winner.proposition,
                    "served_id": winner.id, "evidence": [f.id for f in rivals],
                    "uncorroborated": [f.id for f in overridden],
                    "reason": "user assertion not corroborated — "
                              "the corroborated fact wins"}
        return {"verdict": "ACCEPT", "answer": winner.proposition,
                "served_id": winner.id, "evidence": [f.id for f in rivals],
                "uncorroborated": [], "reason": "unchallenged"}

    best = max(servable, key=_rank)
    others = [f for f in servable if f is not best]
    uncorroborated = [f.id for f in beliefs if _value(f) != _value(best)]
    if all(_rank(best) > _rank(f) for f in others):
        # CORRECT whenever a real conflict was resolved by the label — never
        # dependent on which side recall happened to rank first (that order is
        # not deterministic w.r.t. content, the verdict must be).
        label = (best.epistemic or {}).get("kind", "unlabeled")
        return {"verdict": "CORRECT", "answer": best.proposition,
                "served_id": best.id, "evidence": [f.id for f in rivals],
                "uncorroborated": uncorroborated,
                "reason": f"conflict resolved by epistemic rank: {label} wins"}
    # a tie between conflicting guarantees is a REAL conflict — show, don't pick
    return {"verdict": "ABSTAIN", "answer": None, "served_id": None,
            "evidence": [f.id for f in live],
            "uncorroborated": [f.id for f in beliefs],
            "reason": "conflict_without_epistemic_winner"}
