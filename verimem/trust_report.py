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

from .fact_type import causal_answerable, classify_fact_type, evidence_type_summary
from .temporal_context import _event_ts, _iso, fact_history

__all__ = ["build_trust_report", "TRUST_SCOPE"]

#: What a Verimem trust score DOES and does NOT certify — surfaced in every dossier
#: so a consumer (a judge, an operator) never over-reads it. The causal axis
#: (benchmark/veribench/causal_axis.py) shows why the boundary bites: honest sources
#: can corroborate a spurious correlation, so "corroborated" is NOT "causally true".
TRUST_SCOPE = (
    "Verimem certifies WHO asserted a fact, how independently it was corroborated, "
    "and how fresh it is — NOT that it is causally true. A do(X)/interventional "
    "question needs an interventional-typed fact; a corroborated observational one "
    "cannot answer it (provenance != causality)."
)


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
        "fact_type": classify_fact_type(getattr(fact, "verified_by", None),
                                        getattr(fact, "writer_role", None)),
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


_CE_FLOOR_ENV = "VERIMEM_CE_RELEVANCE_FLOOR"


def _ce_relevance_floor() -> float:
    import os
    try:
        return float(os.environ.get(_CE_FLOOR_ENV, "0.0"))
    except ValueError:
        return 0.0


def _apply_ce_gate(sm, query: str, hits: list) -> tuple[list, bool, bool]:
    """Drop hits the cross-encoder scores as NOT relevant to ``query`` (CE logit
    below :func:`_ce_relevance_floor`, default 0.0). Store-size-independent — the
    CE cleanly separates on-topic (~+8) from off-topic (~-8) where the bi-encoder
    cosine (anisotropic, ~0.7+ for anything) cannot, so a query the store cannot
    support ABSTAINS instead of returning the nearest-but-wrong fact (measured
    2026-07-18: a coffee-machine fact scored bi-encoder 0.71 but CE -8.7 for a
    database query). No-op if the reranker is unavailable (falls back to the
    bi-encoder ``min_relevance`` floor)."""
    if not hits:
        return hits, False, False
    try:
        from .semantic import _load_reranker
        scorer = _load_reranker()
    except Exception:  # noqa: BLE001 — reranker optional; degrade to bi-encoder floor
        scorer = None
    if scorer is None:
        return hits, False, False   # ran=False → caller keeps the bi-encoder floor
    try:
        pairs = [(query or "", getattr(h[0], "proposition", "") or "") for h in hits]
        ce = scorer(pairs)
    except Exception:  # noqa: BLE001 — a scorer fault must not break the read
        return hits, False, False
    floor = _ce_relevance_floor()
    kept = [h for h, s in zip(hits, ce, strict=False) if float(s) >= floor]
    return kept, (len(kept) < len(hits)), True


def build_trust_report(sm, query: str, *, k: int = 5, deep: bool = False,
                       as_of: float | None = None,
                       max_hops: int = 3,
                       min_relevance: float = 0.0,
                       ce_gate: bool = False) -> dict[str, Any]:
    """Build the evidence dossier for ``query``: the retrieved facts with their
    full chain of custody, or an EXPLICIT abstention when the memory holds
    nothing relevant. ``deep`` searches the archive (dormant memories);
    ``as_of`` reconstructs a past moment's state of knowledge.

    ``min_relevance`` (default 0.0 = off, behaviour unchanged) is a retrieval
    floor: hits scoring below it are dropped, so a query with NO relevant fact
    abstains WITHOUT an LLM. Needed because the bi-encoder is anisotropic —
    every query cosine-matches *something* ~0.8, so ``abstained = no hits``
    alone never fires on an absent attribute (surfaced by TrustMem-Bench axis 1,
    which measured relevant top-1 ≥0.842 vs absent ≤0.828 on the synthetic set:
    the floor is model- and corpus-dependent, so it stays opt-in, not a
    baked-in constant)."""
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
    floored = False
    # CE relevance gate (opt-in via explain when abstention is requested): the
    # reliable, store-size-independent floor — drops off-topic hits the bi-encoder
    # cosine cannot. When the CE actually ran it is AUTHORITATIVE (it REPLACES the
    # bi-encoder min_relevance floor, which is the unreliable one it fixes); the
    # bi-encoder floor stays only as the fallback when no reranker is installed.
    ce_ran = False
    if ce_gate:
        hits, ce_floored, ce_ran = _apply_ce_gate(sm, query, hits)
        floored = floored or ce_floored
    if min_relevance > 0.0 and not ce_ran:
        kept = [h for h in hits
                if len(h) > 1 and h[1] is not None and h[1] >= min_relevance]
        floored = floored or (len(kept) < len(hits))
        hits = kept
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
        "min_relevance": min_relevance,
        "generated_at": time.time(),
        "scope": TRUST_SCOPE,
        # the causal moat (Vivarium P38/P49): type the evidence and route — a do(X)
        # claim is answerable ONLY with interventional evidence, never a wall of
        # corroborated observations. Turns TRUST_SCOPE from a disclaimer into a gate.
        "evidence_types": evidence_type_summary(f["fact_type"] for f in facts),
        "causal_answerable": causal_answerable(f["fact_type"] for f in facts),
        "facts": facts,
        "n_facts": len(facts),
        "n_disputed": sum(1 for e in facts if e["disputes"]),
        "n_dormant": sum(1 for e in facts if e["freshness"] == "dormant"),
        "abstained": not facts,
        "reason": (
            "nothing scored above the relevance floor for this query"
            if not facts and floored
            else "no supporting facts in memory for this query"
            if not facts else None),
    }
    return report
