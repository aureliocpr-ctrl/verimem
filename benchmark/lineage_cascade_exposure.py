"""NARRATIVE-descendant exposure of a REAL corpus's lineage_to graph (pure, no LLM).

R24 originally read this as "justification-debt". R26 corrected that: VERIFIED on the real
corpus, the Engram field ``lineage_to`` is a NARRATIVE/session-successor pointer (95%
cross-topic ``clp --lineage-to auto`` chain links), NOT a logical-derivation edge — a
narrative successor does not derive its TRUTH from its predecessor. So this module measures
the lineage_to graph for what it actually is: an UPPER BOUND on how many narrative descendants
a fact has, NOT a count of beliefs that would lose their justification. The true
justification-debt requires a TYPED logical-derivation edge the write-path does not record
yet (see verimem.justified_memory.fact_to_belief, which after R26 ignores lineage_to and reads
only ``derives_from``); until then propagate is correctly dormant (R23).

This reads ``lineage_to`` DIRECTLY (decoupled from fact_to_belief, which now uses the logical
edge). Pure graph computation — reverse-reachability over the lineage_to chain.
"""
from __future__ import annotations

from collections import deque
from typing import Any

from verimem.justified_memory import _attr


def _reverse_graph(facts: list[object]) -> dict[str, set[str]]:
    """child-edges of the NARRATIVE graph: rev[X] = {ids whose lineage_to includes X}. Only
    edges to a present fact are kept (a lineage_to pointing outside the corpus is dangling)."""
    ids = {str(_attr(f, "id", "")) for f in facts}
    rev: dict[str, set[str]] = {}
    for f in facts:
        lt = _attr(f, "lineage_to") or ()
        if isinstance(lt, str):
            lt = [d.strip() for d in lt.strip("[]").split(",") if d.strip()]
        for d in lt:
            d = str(d)
            if d in ids:
                rev.setdefault(d, set()).add(str(_attr(f, "id", "")))
    return rev


def transitive_dependents(root: str, rev: dict[str, set[str]]) -> set[str]:
    """All facts that transitively follow `root` in the narrative graph (BFS), excluding root."""
    out: set[str] = set()
    q = deque(rev.get(root, ()))
    while q:
        n = q.popleft()
        if n in out or n == root:
            continue
        out.add(n)
        q.extend(rev.get(n, ()))
    return out


def run(facts: list[object], *, now: float = 1_000_000.0) -> dict[str, Any]:
    facts = list(facts)
    live_ids = {str(_attr(f, "id", "")) for f in facts if not _attr(f, "superseded_by")}
    superseded_ids = [str(_attr(f, "id", "")) for f in facts if _attr(f, "superseded_by")]
    rev = _reverse_graph(facts)

    foundations = [x for x in rev if x in live_ids]   # live facts with >=1 narrative successor
    cascades = [len(transitive_dependents(x, rev) & live_ids) for x in foundations]
    order = sorted(range(len(foundations)), key=lambda i: cascades[i], reverse=True)
    by_id = {str(_attr(f, "id", "")): f for f in facts}
    top = [{"id": foundations[i], "narrative_descendants": cascades[i],
            "proposition": (_attr(by_id.get(foundations[i]), "proposition", "") or "")[:120]}
           for i in order[:10]]

    return {
        "edge_semantics": "lineage_to = NARRATIVE successor (NOT logical derivation; R26)",
        "metric": "narrative-descendant exposure (UPPER BOUND, not justification-debt)",
        "n_facts": len(facts),
        "n_live": len(live_ids),
        "n_foundations_with_narrative_successors": len(foundations),
        "max_narrative_cascade": max(cascades) if cascades else 0,
        "mean_cascade_over_foundations": round(sum(cascades) / len(cascades), 3) if cascades else 0.0,
        "total_narrative_descendant_exposure": sum(cascades),
        "current_direct_supersessions": len(superseded_ids),
        "current_supersessions_with_narrative_successors":
            sum(1 for s in superseded_ids if transitive_dependents(s, rev)),
        "top_foundations": top,
    }


__all__ = ["transitive_dependents", "run"]
