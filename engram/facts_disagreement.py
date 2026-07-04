"""R37: Heuristic disagreement detection on facts.

Two facts are flagged as potentially contradictory if:
  - their proposition token sets are SIMILAR (jaccard ≥ threshold)
  - one contains a negation/cancellation marker that the other doesn't

Markers: not, no, never, none, patched, fixed, resolved, mitigated,
remediated, withdrawn, deprecated, obsoleted.

This is heuristic — surface candidates for review, not authoritative
NLI. Caller decides which to keep / merge / discard.
"""
from __future__ import annotations

import re
from itertools import combinations
from typing import Any

_TOKEN_RE = re.compile(r"[A-Za-z0-9_\-]+")

_NEGATION_MARKERS = frozenset({
    "not", "no", "never", "none", "without",
    "patched", "fixed", "resolved", "mitigated", "remediated",
    "withdrawn", "deprecated", "obsoleted", "retracted",
    "false", "untrue", "incorrect",
})


def _tokens(text: str) -> set[str]:
    return {t.lower() for t in _TOKEN_RE.findall(text or "")}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def find_disagreements(
    facts: list[Any],
    *,
    sim_threshold: float = 0.5,
    top_k: int = 50,
) -> dict[str, Any]:
    """Pairs of facts likely to contradict each other."""
    pairs: list[dict[str, Any]] = []
    if not facts:
        return {"pairs": [], "n_facts_scanned": 0, "n_pairs": 0}

    cache = {
        getattr(f, "id", ""): (f, _tokens(getattr(f, "proposition", "")))
        for f in facts
    }

    for (id_a, (fa, ta)), (id_b, (fb, tb)) in combinations(cache.items(), 2):
        sim = _jaccard(ta, tb)
        if sim < sim_threshold:
            continue
        # check negation marker asymmetry
        neg_a = ta & _NEGATION_MARKERS
        neg_b = tb & _NEGATION_MARKERS
        # one has marker, other doesn't
        if bool(neg_a) == bool(neg_b):
            continue
        marker = (neg_a or neg_b).pop()
        pairs.append({
            "fact_a": {
                "id": id_a,
                "proposition": getattr(fa, "proposition", "")[:120],
            },
            "fact_b": {
                "id": id_b,
                "proposition": getattr(fb, "proposition", "")[:120],
            },
            "similarity": round(sim, 3),
            "negation_marker": marker,
            "rationale": (
                f"high overlap ({sim:.2f}) but one fact contains '{marker}'"
            ),
        })

    pairs.sort(key=lambda p: -p["similarity"])
    return {
        "pairs": pairs[:top_k],
        "n_facts_scanned": len(facts),
        "n_pairs": len(pairs),
    }


__all__ = ["find_disagreements"]
