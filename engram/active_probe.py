"""Active probes — the store builds the query that would falsify a fact
(Vivarium P87 / cortex ``active_real``: designed probes killed spurious
postulates in ~4 observations where passive observation left them in limbo
forever; the hypothesis trilemma became a budget line).

One probe pass over a copula fact:

  1. build the falsifying query from the fact itself ("<subject> is …" — what
     ELSE does the store assert about this subject?);
  2. counter-evidence = a LIVE fact, same subject, different value, from an
     INDEPENDENT non-engine source (P85: ``actor:*`` rivals never count —
     self-echo cannot refute the world);
  3. found → propose ``refuted(counterexample=<fact-id>: <value>)`` through the
     monotone epistemic rules (set_epistemic — absorbing, auditable);
     survived → the fact's ``unbeaten`` bound grows by one: bound semantics =
     NUMBER OF PROBES SURVIVED, declared here and in the label itself.

Honest scope: probes the store against ITSELF (internal consistency made
active). Probing against external anchors (re-fetching a source, an API
ground-truth) plugs into the same outcome contract later.
"""
from __future__ import annotations

from typing import Any

from .composer import _copula_parse, _strip_article
from .epistemic import make_refuted, make_unbeaten
from .self_provenance import is_self_ref

__all__ = ["probe_fact"]


def probe_fact(mem: Any, fact_id: str, *, k: int = 8) -> dict[str, Any]:
    """One active-falsification pass. Returns ``{outcome, probe_query,
    counterexample_id?, bound?}`` with outcome in
    ``refuted_proposed | survived | not_probeable | not_found``."""
    fact = mem.semantic.get(fact_id)
    if fact is None:
        return {"outcome": "not_found"}
    parsed = _copula_parse(fact.proposition)
    if not parsed:
        return {"outcome": "not_probeable",
                "reason": "no copula structure to falsify (world-bound v1)"}
    subj, obj_norm, _obj_raw = parsed
    probe_query = f"{subj} is"

    hits = mem.search(probe_query, k=k)
    for h in hits:
        rid = h.get("id", "")
        if rid == fact.id:
            continue
        rival = mem.semantic.get(rid)
        if rival is None or rival.superseded_by \
                or rival.status in ("quarantined", "orphaned"):
            continue
        rp = _copula_parse(rival.proposition)
        if not rp or _strip_article(rp[0]).lower() != _strip_article(subj).lower():
            continue
        if rp[1] == obj_norm:
            continue                                   # agreement, not a rival
        if any(is_self_ref(r) for r in (rival.verified_by or [])):
            continue                                   # P85: self-echo can't refute
        label = make_refuted(f"{rival.id}: {rp[1]}")
        applied = mem.semantic.set_epistemic(fact.id, label)
        return {"outcome": "refuted_proposed", "probe_query": probe_query,
                "counterexample_id": rival.id, "label_applied": applied}

    # survived: the bound = probes survived so far, monotone by construction
    current = fact.epistemic if fact.epistemic else None
    bound = (current["bound"] + 1 if current and current["kind"] == "unbeaten"
             else 1)
    applied = mem.semantic.set_epistemic(fact.id, make_unbeaten(bound))
    return {"outcome": "survived", "probe_query": probe_query,
            "bound": bound, "label_applied": applied}
