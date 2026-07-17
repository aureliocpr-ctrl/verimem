"""Phase-4 epistemic health — a memory that knows the epistemic state of what it holds.

The flagship "epistemic memory" capability. A normal memory trusts everything it stored;
this one can AUDIT itself and report, per stored fact: is it GROUNDED (a source actually
entails it), FRESH (not stale), and UNCONTESTED — then aggregate into one health score.
That lets the system say "X% of my 'verified' facts are actually grounded; the rest are
provenance-less or unsupported" and act on it (re-verify, downgrade, or refuse to serve).

Design is PURE: the expensive per-fact checks (grounding via the LLM gate, freshness,
contradiction) are INJECTED callables, so the aggregation logic is unit-tested
deterministically with stubs. The live audit wires
``verimem.grounding_gate.fact_grounding_score`` as the grounder and
``verimem.freshness``/``time_decay`` as the freshness check. O5: the grounder is the only
LLM cost, and it is sampled (audit a subset), never the whole corpus per call.
"""
from __future__ import annotations

import statistics
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

# Default grounded threshold mirrors grounding_gate.DEFAULT_THRESHOLD; passed in explicitly
# at call sites so this module has no import-time dependency on the gate.
_DEFAULT_THRESHOLD = 85.0


@dataclass
class FactAudit:
    """Per-fact epistemic verdict. ``grounded``/``fresh`` are None when not checkable
    (no source to ground against / no freshness signal) — distinct from False."""

    fact_id: str
    has_source: bool
    grounded: bool | None
    fresh: bool | None
    contested: bool


def _source_of(fact: Any) -> str | None:
    """Provenance text a fact was derived from, if any. Engram facts may carry it as
    ``source`` or a span under ``provenance``/``grounding_span``; absent on legacy facts."""
    for attr in ("source", "provenance", "grounding_span"):
        v = getattr(fact, attr, None)
        if isinstance(v, str) and v.strip():
            return v
    if isinstance(fact, dict):
        for k in ("source", "provenance", "grounding_span"):
            v = fact.get(k)
            if isinstance(v, str) and v.strip():
                return v
    return None


def audit_one(fact: Any, *, grounder: Callable[[str, str], float],
              threshold: float = _DEFAULT_THRESHOLD,
              freshness_fn: Callable[[Any], bool] | None = None,
              contested_fn: Callable[[Any], bool] | None = None) -> FactAudit:
    """Audit a single fact. ``grounder(source, proposition) -> score 0-100``. A fact with
    no source is grounded=None (unauditable, NOT failed). Pure given the injected checks."""
    fid = str(getattr(fact, "id", None) or (fact.get("id") if isinstance(fact, dict) else ""))
    prop = getattr(fact, "proposition", None) or (
        fact.get("proposition") if isinstance(fact, dict) else "") or ""
    src = _source_of(fact)
    grounded: bool | None = None
    if src:
        grounded = grounder(src, prop) >= threshold
    fresh = freshness_fn(fact) if freshness_fn else None
    contested = bool(contested_fn(fact)) if contested_fn else False
    return FactAudit(fact_id=fid, has_source=bool(src), grounded=grounded,
                     fresh=fresh, contested=contested)


def health_report(audits: list[FactAudit]) -> dict[str, Any]:
    """Aggregate per-fact audits into a corpus health report. Components are each in [0,1];
    the composite is the mean of the AVAILABLE components (a corpus with no freshness signal
    still gets a grounding-based score). provenance_coverage is reported separately because
    it bounds how much of the corpus is even grounding-auditable."""
    n = len(audits)
    if n == 0:
        return {"n": 0, "composite": None}
    with_src = [a for a in audits if a.has_source]
    grounded_audited = [a for a in with_src if a.grounded is not None]
    fresh_audited = [a for a in audits if a.fresh is not None]

    provenance_coverage = len(with_src) / n
    grounded_fraction = (sum(1 for a in grounded_audited if a.grounded) / len(grounded_audited)
                         if grounded_audited else None)
    fresh_fraction = (sum(1 for a in fresh_audited if a.fresh) / len(fresh_audited)
                      if fresh_audited else None)
    uncontested_fraction = sum(1 for a in audits if not a.contested) / n

    # composite = mean of available component scores. grounded_fraction is weighted by
    # provenance_coverage (an ungrounded-able corpus cannot claim full grounding health).
    components: list[float] = []
    if grounded_fraction is not None:
        components.append(grounded_fraction * provenance_coverage)
    if fresh_fraction is not None:
        components.append(fresh_fraction)
    components.append(uncontested_fraction)
    composite = round(statistics.mean(components), 3) if components else None

    return {
        "n": n,
        "provenance_coverage": round(provenance_coverage, 3),
        "grounded_fraction": round(grounded_fraction, 3) if grounded_fraction is not None else None,
        "n_grounding_audited": len(grounded_audited),
        "fresh_fraction": round(fresh_fraction, 3) if fresh_fraction is not None else None,
        "uncontested_fraction": round(uncontested_fraction, 3),
        "composite": composite,
        "ungrounded_fact_ids": [a.fact_id for a in grounded_audited if a.grounded is False],
    }


def audit_corpus(facts: list[Any], *, grounder: Callable[[str, str], float],
                 threshold: float = _DEFAULT_THRESHOLD,
                 freshness_fn: Callable[[Any], bool] | None = None,
                 contested_fn: Callable[[Any], bool] | None = None) -> dict[str, Any]:
    """Audit a list of facts and return the health report. The driver; ``facts`` is the
    caller's sample (audit a subset to bound LLM cost)."""
    audits = [audit_one(f, grounder=grounder, threshold=threshold,
                        freshness_fn=freshness_fn, contested_fn=contested_fn) for f in facts]
    return health_report(audits)


__all__ = ["FactAudit", "audit_one", "health_report", "audit_corpus"]
