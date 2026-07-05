"""TrustReport — the evidence dossier behind an answer (F3, iter 47).

Mandate ("affidabile per un GIUDICE"): every answer must be able to show its
chain of custody. This module makes the trust stack ATOMIC — one
JSON-serializable object per query that declares:

  * ``facts``    — the evidence actually retrieved, each with WHAT
    (proposition), WHERE FROM (provenance, writer_role), HOW TRUSTED (status,
    verified_by, grounding_score, confidence), the TWO CLOCKS (asserted_at =
    when true, created_at = when learned), its freshness (live vs dormant),
    what it REPLACED (supersession history) and what it CONFLICTS with
    (declared unresolved disputes);
  * ``abstained`` — an explicit "I have nothing" verdict with its reason,
    instead of a guess (the anti-confab contract, surfaced);
  * ``as_of`` support — the dossier can be built for a PAST moment (the
    lawyer's "state of knowledge at signature date").

Pure read-side composition of existing surfaces (recall / temporal_context /
ContradictionStore): no LLM, no schema change, fail-safe per fact.
"""
from __future__ import annotations

import time
from typing import Any

from .temporal_context import _event_ts, _iso, fact_history

__all__ = ["build_trust_report"]


def _fact_evidence(sm, fact, cs, *, max_hops: int = 3,
                   score: float | None = None) -> dict[str, Any]:
    """One fact's full custody record. Best-effort: a history/dispute lookup
    error degrades to the plain record — the dossier never fails to build.
    ``score`` is the retrieval relevance (cosine): the dossier DECLARES weak
    relevance instead of hiding it (glass contract). NB known limit: recall has
    no relevance floor, so on a small store an off-domain query still returns
    top-k (e5 anisotropy ~0.8 baseline) — the consumer must read the score;
    an evidence-floor is an open item (answer-side abstention is the measured
    mechanism, ENGRAM_GROUNDING_GATE)."""
    now = time.time()
    created = getattr(fact, "created_at", None)
    asserted = getattr(fact, "asserted_at", None)
    lv = getattr(fact, "last_verified_at", None) or created
    age_days = (now - float(lv)) / 86400.0 if lv is not None else None
    ev: dict[str, Any] = {
        "id": getattr(fact, "id", ""),
        "relevance": round(float(score), 4) if score is not None else None,
        "proposition": getattr(fact, "proposition", ""),
        "topic": getattr(fact, "topic", ""),
        "status": getattr(fact, "status", ""),
        "confidence": getattr(fact, "confidence", None),
        "provenance": list(getattr(fact, "source_episodes", []) or []),
        "writer_role": getattr(fact, "writer_role", None),
        "verified_by": getattr(fact, "verified_by", None),
        "grounding_score": getattr(fact, "grounding_score", None),
        "asserted_at": asserted,
        "asserted_date": _iso(_event_ts(fact)),
        "created_at": created,
        "age_days": round(age_days, 1) if age_days is not None else None,
        "freshness": ("dormant" if (age_days is not None and age_days > 45.0)
                      else "live"),
        "history": [],
        "disputes": [],
    }
    try:
        ev["history"] = [
            {"proposition": getattr(p, "proposition", ""),
             "asserted_date": _iso(_event_ts(p)),
             "superseded_at": getattr(p, "superseded_at", None),
             "reason": getattr(p, "superseded_reason", None)}
            for p in fact_history(sm, fact.id, max_hops=max_hops)
        ]
    except Exception:  # noqa: BLE001 — dossier must never fail on enrichment
        pass
    try:
        if cs is not None:
            for c in cs.list_unresolved_for_fact(fact.id):
                other_id = (c.fact_b_id if c.fact_a_id == fact.id
                            else c.fact_a_id)
                other = sm.get(other_id)
                if other is not None and not getattr(
                        other, "superseded_by", None):
                    ev["disputes"].append({
                        "id": other_id,
                        "proposition": getattr(other, "proposition", ""),
                        "kind": getattr(c, "kind", ""),
                    })
    except Exception:  # noqa: BLE001
        pass
    return ev


def build_trust_report(sm, query: str, *, k: int = 5, deep: bool = False,
                       as_of: float | None = None,
                       max_hops: int = 3) -> dict[str, Any]:
    """Build the evidence dossier for ``query``: the retrieved facts with their
    full chain of custody, or an EXPLICIT abstention when the memory holds
    nothing relevant. ``deep`` searches the archive (dormant memories);
    ``as_of`` reconstructs a past moment's state of knowledge."""
    cs = None
    try:
        from .contradiction import ContradictionStore
        cs = ContradictionStore(sm.db_path)
    except Exception:  # noqa: BLE001 — disputes are an enrichment
        cs = None
    if as_of is not None:
        from .temporal_context import recall_as_of
        hits = recall_as_of(sm, query, when=float(as_of), k=k)
    else:
        hits = sm.recall(query or "", k=k, deep=deep)
    facts = [
        _fact_evidence(sm, h[0], cs, max_hops=max_hops,
                       score=(h[1] if len(h) > 1 else None))
        for h in hits
    ]
    report: dict[str, Any] = {
        "query": query,
        "as_of": as_of,
        "deep": bool(deep),
        "k": k,
        "generated_at": time.time(),
        "facts": facts,
        "n_facts": len(facts),
        "n_disputed": sum(1 for e in facts if e["disputes"]),
        "n_dormant": sum(1 for e in facts if e["freshness"] == "dormant"),
        "abstained": not facts,
        "reason": ("no supporting facts in memory for this query"
                   if not facts else None),
    }
    return report
