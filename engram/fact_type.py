"""Earned fact TYPE — observational / interventional / derived (the causal moat).

Vivarium P38/P49 (docs/SYNTHESIS.md, PRODUCT-BRAIN.md component 7): trust certifies
WHO-said-it-and-corroborated, which is ORTHOGONAL to causal truth. Honest sources
agree on a spurious X~Y (a latent confounder Z drives both), so a trust-only memory
answers a do(X) question confidently and is WRONG. The measured lift comes from
ROUTING by a typed provenance: a causal claim is supported only by INTERVENTIONAL
evidence (a recorded do(X)→Y), never by a corroborated OBSERVATION — "type + trust are
both necessary" (P49, typed_trust 0.654 = oracle vs blind 0.495). No memory vendor in
2026 ships this; it makes the scope-declaration (engram/trust_report.TRUST_SCOPE)
ENFORCEABLE instead of merely stated.

The type is EARNED from the fact's provenance (pure function of verified_by /
writer_role — no schema change, no LLM):
  * ``interventional`` — an experiment / intervention / trial / RCT / A-B-test record
    (a do(X)→Y observation), the only evidence that answers a causal query.
  * ``derived``        — a multi-hop derivation / inference (its trust needs the CHAIN
    re-grounded, not the producer's reputation — P75/L3).
  * ``observational``  — the default: a plain corroborated observation. Trustworthy as
    "who said it & corroborated", but it CANNOT settle causation.
"""
from __future__ import annotations

from collections.abc import Iterable

OBSERVATIONAL = "observational"
INTERVENTIONAL = "interventional"
DERIVED = "derived"

# writer_role values that DECLARE the kind of record (client-set, like gate_router).
_INTERV_ROLES = frozenset({"experiment", "intervention", "interventional", "trial",
                           "rct", "ab_test", "ab-test"})
_DERIVED_ROLES = frozenset({"derived", "derivation", "reasoning", "inference",
                            "inferred"})

# verified_by ref prefixes that anchor a fact to an intervention or a derivation.
_INTERV_PREFIXES = ("experiment:", "intervention:", "trial:", "rct:", "ab-test:",
                    "abtest:", "do:")
_DERIVED_PREFIXES = ("derived-from:", "derivation:", "reasoning:", "inferred:",
                     "traced:")


def classify_fact_type(verified_by: Iterable[str] | None,
                       writer_role: str | None = None) -> str:
    """The earned type of a fact from its provenance. Declared role wins (explicit);
    else the first typing ref in ``verified_by``; else ``observational`` (the honest,
    least-causal default — a plain observation never silently claims interventional
    authority)."""
    role = (writer_role or "").strip().lower()
    if role in _INTERV_ROLES:
        return INTERVENTIONAL
    if role in _DERIVED_ROLES:
        return DERIVED
    for ref in verified_by or ():
        r = str(ref).strip().lower()
        if r.startswith(_INTERV_PREFIXES):
            return INTERVENTIONAL
        if r.startswith(_DERIVED_PREFIXES):
            return DERIVED
    return OBSERVATIONAL


def causal_answerable(fact_types: Iterable[str]) -> bool:
    """Can a do(X)/causal claim be settled by this evidence set? Only if at least one
    INTERVENTIONAL fact is present — a wall of corroborated observations cannot (P38).
    This is the routing rule that turns the scope-declaration into a gate."""
    return any(t == INTERVENTIONAL for t in fact_types)


def evidence_type_summary(fact_types: Iterable[str]) -> dict[str, int]:
    """Counts per type — the dossier's at-a-glance 'what kind of evidence is this?'."""
    out = {OBSERVATIONAL: 0, INTERVENTIONAL: 0, DERIVED: 0}
    for t in fact_types:
        if t in out:
            out[t] += 1
    return out


__all__ = ["OBSERVATIONAL", "INTERVENTIONAL", "DERIVED", "classify_fact_type",
           "causal_answerable", "evidence_type_summary"]
