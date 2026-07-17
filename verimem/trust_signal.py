"""Cycle #117 (2026-05-17) — Memory self-doubt layer.

Aurelio direttiva (laboratorio mode, pensiero ampio):

   "HippoAgent non sa quando NON FIDARSI DI SÉ. Recall ritorna fact
   con cosine alta, ma NON dice 'questo fact ha 3 contradiction
   associate, age=180 giorni, è stato corretto 2 volte'. Sessione
   futura usa il fact come verità → propaga errore."

This module computes a live `TrustSignal` for any Fact at recall time.
It combines four independent signals:

* **Supersession**: fact.superseded_by is set → ``obsolete``.
* **Contradictions**: ContradictionStore has unresolved rows pointing
  at this fact_id → ``contested``.
* **Age**: created_at older than ``stale_age_days`` (default 180) →
  ``stale``.
* **Status**: ``legacy_unverified`` (or low-confidence ``model_claim``)
  → ``unverified``.
* Otherwise → ``trusted``.

The function is **pure** (no I/O beyond the optional ContradictionStore
query). Callers attach it to recall results so the LLM sees both the
content AND the meta-trust verdict.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .contradiction import ContradictionStore
    from .semantic import Fact, SemanticMemory


_STALE_AGE_DAYS_DEFAULT = 180.0
_LOW_CONFIDENCE_THRESHOLD = 0.5


@dataclass(frozen=True)
class TrustSignal:
    """Live meta-trust verdict on a single Fact.

    Attributes:
        verdict: one of ``trusted`` | ``stale`` | ``contested`` |
            ``obsolete`` | ``unverified``.
        age_days: how old the fact is (created_at vs now).
        n_contradictions: unresolved contradictions involving the fact
            id (0 if no ContradictionStore was provided).
        is_superseded: True iff ``fact.superseded_by`` is set.
        details: short human-readable explanation of the verdict.
    """
    verdict: str
    age_days: float
    n_contradictions: int
    is_superseded: bool
    details: str = ""


def compute_trust_signal(
    fact: Fact,
    sm: SemanticMemory,
    *,
    now: float | None = None,
    contradiction_store: ContradictionStore | None = None,
    stale_age_days: float = _STALE_AGE_DAYS_DEFAULT,
    low_confidence_threshold: float = _LOW_CONFIDENCE_THRESHOLD,
) -> TrustSignal:
    """Compute the trust signal for ``fact``.

    Priority order (highest concern wins):
      1. obsolete (superseded)
      2. contested (unresolved contradiction in store)
      3. stale (older than ``stale_age_days``)
      4. unverified (legacy_unverified status OR low-confidence model_claim)
      5. trusted (default)

    Args:
        fact: the fact to assess.
        sm: SemanticMemory (kept as parameter to allow future extensions
            like usage-frequency, even if V1 doesn't query it).
        now: optional epoch override (tests use a fixed clock).
        contradiction_store: optional ContradictionStore. Without it
            the contested-verdict path is disabled and n_contradictions=0.
        stale_age_days: threshold past which a fact is "stale".
        low_confidence_threshold: facts with confidence below this AND
            status=model_claim are flagged "unverified".
    """
    now_ts = float(now if now is not None else time.time())
    age_days = max(0.0, (now_ts - float(fact.created_at)) / 86400.0)
    is_superseded = bool(fact.superseded_by)

    # 1. obsolete — strongest signal: explicitly superseded.
    if is_superseded:
        return TrustSignal(
            verdict="obsolete",
            age_days=age_days,
            n_contradictions=0,
            is_superseded=True,
            details=(
                f"superseded_by={fact.superseded_by} "
                f"reason={fact.superseded_reason!r}"
            ),
        )

    # 2. contested — unresolved contradiction(s) involving this fact.
    n_contra = 0
    if contradiction_store is not None:
        n_contra = len(
            contradiction_store.list_unresolved_for_fact(fact.id)
        )
        if n_contra > 0:
            return TrustSignal(
                verdict="contested",
                age_days=age_days,
                n_contradictions=n_contra,
                is_superseded=False,
                details=f"unresolved_contradictions={n_contra}",
            )

    # 3. stale — older than the threshold.
    if age_days >= stale_age_days:
        return TrustSignal(
            verdict="stale",
            age_days=age_days,
            n_contradictions=n_contra,
            is_superseded=False,
            details=f"age={age_days:.0f}d >= {stale_age_days:.0f}d",
        )

    # 4. unverified — legacy or low-confidence model_claim.
    status = getattr(fact, "status", "model_claim")
    if status == "legacy_unverified":
        return TrustSignal(
            verdict="unverified",
            age_days=age_days,
            n_contradictions=n_contra,
            is_superseded=False,
            details="status=legacy_unverified",
        )
    if status == "model_claim" and float(fact.confidence) < low_confidence_threshold:
        return TrustSignal(
            verdict="unverified",
            age_days=age_days,
            n_contradictions=n_contra,
            is_superseded=False,
            details=(
                f"status=model_claim conf={fact.confidence:.2f} < "
                f"{low_confidence_threshold:.2f}"
            ),
        )

    # 5. trusted by default.
    return TrustSignal(
        verdict="trusted",
        age_days=age_days,
        n_contradictions=n_contra,
        is_superseded=False,
        details=f"status={status} conf={fact.confidence:.2f} age={age_days:.0f}d",
    )


__all__ = ["TrustSignal", "compute_trust_signal"]
