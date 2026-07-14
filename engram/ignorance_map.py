"""The ignorance map — "I don't know" upgraded to "here is WHAT I'm missing".

Vivarium P83 / cortex cognition, via the handoff: diagnosing WHICH
sub-competence is missing made acquiring it ~6.2× cheaper than blind
exploration, and the lab's ignorance map motivated all six of its world-bound
abstentions. Product incarnation: for each query the store cannot (or should
not) answer, name the ignorance CLASS and what would cure it —

  * ``no_evidence``       — nothing relevant in the store at all;
  * ``below_floor``       — hits exist but none clears the abstention floor τ
                            (the honest-uncertainty band);
  * ``quarantined_only``  — evidence EXISTS but every piece of it is
                            quarantined: the cure is a supporting source or a
                            quarantine review, not more retrieval;
  * ``conflict``          — live facts about the same subject disagree with no
                            epistemic winner: the cure is an independent
                            source or an audit;
  * ``answerable``        — not ignorance (counted for the honest denominator).

Read-only: the map never writes. It is the daemon's future work-list — every
class maps to a concrete acquisition action.
"""
from __future__ import annotations

import re
from typing import Any

from .composer import _copula_parse, _strip_article

__all__ = ["ignorance_map"]

_WORD = re.compile(r"[a-zA-ZÀ-ɏ0-9]{3,}")
_STOP = frozenset("the and for with what which who how why does is are was "
                  "were this that from into about".split())


def _keywords(text: str) -> set[str]:
    return {w.lower() for w in _WORD.findall(text or "")
            if w.lower() not in _STOP}


def _quarantined_overlap(semantic: Any, query: str, *, min_shared: int = 2) -> bool:
    """Does QUARANTINED evidence share >= min_shared content words with the
    query? Linear scan, declared v1 (the map is an offline diagnostic)."""
    qk = _keywords(query)
    if not qk:
        return False
    for fact in semantic.all():
        if fact.status != "quarantined":
            continue
        if len(qk & _keywords(fact.proposition)) >= min_shared:
            return True
    return False


def _classify(mem: Any, query: str, *, floor: float, k: int) -> dict[str, Any]:
    hits = mem.search(query, k=k)
    top = hits[0].get("score", 0.0) if hits else None
    row: dict[str, Any] = {"query": query, "top_score": top}
    # CONFLICT dominates the floor: when the retrieved facts CONTRADICT each
    # other about one subject, that is the deepest reason the query is
    # unanswerable — a low top score is the symptom, not the diagnosis (the
    # compressed e5 band routinely puts real conflicts under τ).
    by_subject: dict[str, dict[str, list[str]]] = {}
    for h in hits:
        fact = mem.semantic.get(h.get("id", ""))
        if not fact:
            continue
        parsed = _copula_parse(fact.proposition)
        if not parsed:
            continue
        subj = _strip_article(parsed[0]).lower()
        by_subject.setdefault(subj, {}).setdefault(parsed[1], []).append(fact.id)
    qk = _keywords(query)
    for subj, values in by_subject.items():
        # pertinence guard: an off-topic query can retrieve a conflicting pair
        # as mere nearest-neighbour noise — the conflict only explains THIS
        # query's ignorance if the disputed subject is what the query asks about
        if len(values) > 1 and (_keywords(subj) & qk):
            ids = [i for ids_ in values.values() for i in ids_]
            row.update({"class": "conflict", "conflicting_ids": ids,
                        "what_would_help": f"an independent source (or an "
                        f"audit) to resolve '{subj}' — "
                        f"{len(values)} live values disagree"})
            return row
    if not hits or (top or 0.0) < floor:
        if _quarantined_overlap(mem.semantic, query):
            row.update({"class": "quarantined_only",
                        "what_would_help": "evidence exists but is quarantined "
                        "— provide a supporting source or review the quarantine"})
        elif not hits:
            row.update({"class": "no_evidence",
                        "what_would_help": "a source about: "
                        + ", ".join(sorted(_keywords(query))[:5])})
        else:
            row.update({"class": "below_floor",
                        "what_would_help": f"stronger evidence — best hit "
                        f"{top:.2f} sits under the declared floor {floor:.2f}"})
        return row
    row.update({"class": "answerable", "what_would_help": None})
    return row


def ignorance_map(mem: Any, queries: list[str], *, floor: float = 0.8,
                  k: int = 5) -> dict[str, Any]:
    """Classify every query; return ``{queries: [...], by_class: {...}}`` —
    every class counted, nothing silently dropped."""
    rows = [_classify(mem, q, floor=floor, k=k) for q in queries]
    by_class: dict[str, int] = {}
    for r in rows:
        by_class[r["class"]] = by_class.get(r["class"], 0) + 1
    return {"queries": rows, "by_class": by_class,
            "floor": floor, "n": len(rows)}
