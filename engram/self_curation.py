"""Cycle #118 (2026-05-17) — Memory self-curation autonomous loop V1.

Aurelio direttiva (laboratorio mode): "memoria AI-driven pilotata da te,
sperimenta". Misura empirica FASE 1 sui 232 contradictions live (cycle
#110.B detector) ha falsificato l'ipotesi originale di auto-supersede
aggressive: 96% sono AMBIGUOUS (age_delta=0 conf_delta=0), 0% sono
safe_supersede, 0% newer_wins. Solo 3% sono FP_LIKELY (false positive
del detector cycle #110.B su pattern STRENGTHS/WEAKNESS sectioning del
cycle #77 L3 detector).

Quindi V1 è sobrio: solo gestione della ``ContradictionStore`` —
ZERO mutazione dei Fact reali — con due operazioni:

1. ``classify_contradiction(c, a, b)`` — pure decision: returns one of
   ``safe_supersede`` | ``newer_wins`` | ``fp_likely`` | ``ambiguous``
   | ``dangling``.
2. ``auto_resolve_false_positives(sm, store)`` — applica ``store.resolve()``
   solo alle pair ``fp_likely``, marcandole con note ``auto_fp_complementary``.
3. ``audit_contradictions(sm, store)`` — riassunto della distribuzione
   bucket senza mutazione (visibility-only).

NO supersession dei Fact. NO LLM call (cycle 118 mantiene zero cost
extra subscription). NO auto-mutate degli ambiguous.
"""
from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .contradiction import Contradiction, ContradictionStore
    from .semantic import Fact, SemanticMemory


_FP_AGE_MAX_DAYS = 30.0
_FP_CONF_MIN = 0.9
_NEWER_AGE_DELTA_DAYS = 60.0
_NEWER_CONF_DELTA_MIN = 0.15

_AUTO_FP_NOTE = "auto_fp_complementary"


def classify_contradiction(
    c: Contradiction,
    a: Fact | None,
    b: Fact | None,
) -> str:
    """Bucket a contradiction pair into an auto-action class.

    Order matters: returns the FIRST bucket that matches.

    * ``dangling`` — either fact is missing from SemanticMemory.
    * ``safe_supersede`` — at least one fact has ``superseded_by`` set.
      We just close the contradiction (the supersession already
      expressed the human/system decision).
    * ``newer_wins`` — large age delta AND large confidence delta on
      the newer side. Safe-ish to mark old fact as superseded, but V1
      leaves this for human review.
    * ``fp_likely`` — boolean_clash + both confidence >= 0.9 + age
      delta <= 30 days. Pattern of the cycle #77 L3 detector firing on
      complementary sections (STRENGTHS/WEAKNESS, VERDICT/REMARKS),
      NOT real polarity inversion.
    * ``ambiguous`` — everything else. Needs human / LLM review.
    """
    if a is None or b is None:
        return "dangling"

    if bool(a.superseded_by) or bool(b.superseded_by):
        return "safe_supersede"

    age_delta_days = abs(float(a.created_at) - float(b.created_at)) / 86400.0
    conf_delta = abs(float(a.confidence) - float(b.confidence))

    if (
        age_delta_days >= _NEWER_AGE_DELTA_DAYS
        and conf_delta >= _NEWER_CONF_DELTA_MIN
    ):
        return "newer_wins"

    if (
        c.kind == "boolean_clash"
        and min(float(a.confidence), float(b.confidence)) >= _FP_CONF_MIN
        and age_delta_days <= _FP_AGE_MAX_DAYS
    ):
        return "fp_likely"

    return "ambiguous"


def auto_resolve_false_positives(
    sm: SemanticMemory,
    store: ContradictionStore,
) -> dict[str, int]:
    """Auto-resolve only the ``fp_likely`` bucket.

    Returns a report::

        {
            "scanned": int,    # total unresolved contradictions inspected
            "resolved": int,   # marked resolved with auto_fp_complementary note
            "skipped": int,    # not fp_likely (kept unresolved)
            "dangling": int,   # one or both facts missing from sm
        }
    """
    unresolved = store.list_unresolved(limit=10_000)
    scanned = len(unresolved)
    resolved = 0
    skipped = 0
    dangling = 0

    for c in unresolved:
        a = sm.get(c.fact_a_id)
        b = sm.get(c.fact_b_id)
        bucket = classify_contradiction(c, a, b)
        if bucket == "dangling":
            dangling += 1
            continue
        if bucket == "fp_likely":
            if store.resolve(c.id, note=_AUTO_FP_NOTE):
                resolved += 1
            else:
                skipped += 1
            continue
        skipped += 1

    return {
        "scanned": scanned,
        "resolved": resolved,
        "skipped": skipped,
        "dangling": dangling,
    }


def audit_contradictions(
    sm: SemanticMemory,
    store: ContradictionStore,
) -> dict[str, Any]:
    """Audit-only: classify every unresolved contradiction without
    mutating the store. Returns bucket counts + a small sample per
    bucket for human inspection.
    """
    unresolved = store.list_unresolved(limit=10_000)
    buckets: dict[str, int] = {
        "safe_supersede": 0,
        "newer_wins": 0,
        "fp_likely": 0,
        "ambiguous": 0,
        "dangling": 0,
    }
    samples: dict[str, list[dict[str, Any]]] = {k: [] for k in buckets}

    for c in unresolved:
        a = sm.get(c.fact_a_id)
        b = sm.get(c.fact_b_id)
        bucket = classify_contradiction(c, a, b)
        buckets[bucket] = buckets.get(bucket, 0) + 1
        if len(samples[bucket]) < 3:
            samples[bucket].append({
                "contradiction_id": c.id,
                "kind": c.kind,
                "fact_a_id": c.fact_a_id,
                "fact_b_id": c.fact_b_id,
            })

    return {
        "total_unresolved": len(unresolved),
        "buckets": buckets,
        "samples": samples,
        "audited_at": time.time(),
    }


__all__ = [
    "classify_contradiction",
    "auto_resolve_false_positives",
    "audit_contradictions",
]
