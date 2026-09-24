"""Cycle #116 (2026-05-17) — Live memory coherence check.

Direttiva 2026-05-17 (laboratorio mode):

   "hippo_remember oggi è write-only naive. Quando salvi un fact
   non controlli se esiste già un fact simile/correlato → duplicati;
   non triggeri contradiction scan → contraddizioni invisibili;
   non marchi superseded il fact precedente → 2 ricordi co-validi;
   sessione futura recall → trova entrambi → propaga errore."

This module adds a **post-store coherence check** that runs on the
LOCAL topic only (cheap: typically <50 sibling facts per topic) and
returns structured warnings. The caller decides what to do — log,
emit observability event, or store in a `coherence_warnings` table.

Design choices (V1):
* CONSERVATIVE: no mutation, no auto-supersede. Observational only.
* Topic-scoped: only fact with the same ``fact.topic`` are compared.
  Cross-topic scans are out of scope (cycle #110.B already does them
  via the daemon path).
* Reuses ``verimem.contradiction`` primitives (_has_negation, _cosine),
  and since 24/09 (T175) decides numeric clashes with the SHARED detector
  ``quantity_match.numeric_conflict`` — the same decision as the write path
  and the batch, not a second compare on bare numbers.
* Adds `near_duplicate` (token-Jaccard >= 0.7) which the daemon
  detector does NOT cover — this is the specific gap that the
  write-time hook addresses.

Three warning kinds:
* ``near_duplicate``: token-Jaccard above threshold (default 0.7).
* ``numeric_clash``: same topic, similarity >= 0.75, and the shared
  detector sees ONE quantity changed with nothing else different
  (``value_tolerance`` is accepted for compatibility and no longer used).
* ``boolean_clash``: same topic, similarity >= 0.75, exactly one
  side carries a negation marker.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .contradiction import (
    _cosine,
    _has_negation,
)
from .quantity_match import numeric_conflict

if TYPE_CHECKING:
    from .semantic import Fact, SemanticMemory


_TOKEN_RE = re.compile(r"[a-zA-Z0-9]+")

# Defaults tuned conservatively to keep false positives down.
_DEFAULT_JACCARD_THRESHOLD = 0.7
_DEFAULT_NUMERIC_SIM_THRESHOLD = 0.75
_DEFAULT_BOOLEAN_SIM_THRESHOLD = 0.75
_DEFAULT_VALUE_TOLERANCE = 0.05


@dataclass(frozen=True)
class CoherenceWarning:
    """One concern raised by the coherence check.

    Attributes:
        kind: ``"near_duplicate"`` | ``"numeric_clash"`` | ``"boolean_clash"``
        other_fact_id: the sibling fact that triggered the concern.
        details: short human-readable context (e.g. "jaccard=0.83",
            "numbers: [5.0] vs [50.0]").
    """
    kind: str
    other_fact_id: str
    details: str = ""


def _tokenize(text: str) -> set[str]:
    return {t.lower() for t in _TOKEN_RE.findall(text or "") if len(t) > 1}


def _jaccard(a: str, b: str) -> float:
    ta, tb = _tokenize(a), _tokenize(b)
    if not ta and not tb:
        return 1.0
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    union = len(ta | tb)
    return inter / union if union else 0.0


def check_against_siblings(
    fact: Fact,
    siblings: list[Fact],
    *,
    jaccard_threshold: float = _DEFAULT_JACCARD_THRESHOLD,
    numeric_sim_threshold: float = _DEFAULT_NUMERIC_SIM_THRESHOLD,
    boolean_sim_threshold: float = _DEFAULT_BOOLEAN_SIM_THRESHOLD,
    value_tolerance: float = _DEFAULT_VALUE_TOLERANCE,
) -> list[CoherenceWarning]:
    """Compare ``fact`` against each sibling, return one or more warnings
    if any incoherence is detected. Pure function — no side effects.

    The function checks in this order: near_duplicate → numeric_clash →
    boolean_clash. A single sibling can raise multiple warnings (e.g.,
    a near-duplicate that also has a numeric clash).
    """
    out: list[CoherenceWarning] = []
    new_negation = _has_negation(fact.proposition or "")

    for sib in siblings:
        if sib.id == fact.id:
            continue
        # 1. token Jaccard near-duplicate
        jac = _jaccard(fact.proposition or "", sib.proposition or "")
        if jac >= jaccard_threshold:
            out.append(CoherenceWarning(
                kind="near_duplicate",
                other_fact_id=sib.id,
                details=f"jaccard={jac:.2f}",
            ))

        # 2. numeric clash — only worth the cosine call if the SHARED numeric
        # detector sees one (T175, 24/09: the same decision as the write path
        # and the batch, instead of a second compare on bare numbers;
        # `value_tolerance` no longer applies).
        clash = numeric_conflict(fact.proposition or "", sib.proposition or "")
        if clash is not None:
            sim = _cosine(fact, sib)
            if sim >= numeric_sim_threshold:
                unit, va, vb = clash
                out.append(CoherenceWarning(
                    kind="numeric_clash",
                    other_fact_id=sib.id,
                    details=f"{unit}: {va:g} vs {vb:g} sim={sim:.2f}",
                ))

        # 3. boolean clash — exactly one side carries a negation marker.
        sib_negation = _has_negation(sib.proposition or "")
        if new_negation != sib_negation:
            sim = _cosine(fact, sib)
            if sim >= boolean_sim_threshold:
                out.append(CoherenceWarning(
                    kind="boolean_clash",
                    other_fact_id=sib.id,
                    details=(
                        f"new_negation={new_negation} sib_negation="
                        f"{sib_negation} sim={sim:.2f}"
                    ),
                ))
    return out


def scan_topic_for_warnings(
    fact: Fact,
    sm: SemanticMemory,
    **kwargs,
) -> list[CoherenceWarning]:
    """Fetch all sibling fact under the same topic and run
    :func:`check_against_siblings`. Self is automatically excluded.

    ``**kwargs`` is forwarded to ``check_against_siblings`` for
    threshold overrides.
    """
    siblings = [
        f for f in sm.all()
        if f.topic == fact.topic and f.id != fact.id
    ]
    if not siblings:
        return []
    return check_against_siblings(fact, siblings, **kwargs)


__all__ = [
    "CoherenceWarning",
    "check_against_siblings",
    "scan_topic_for_warnings",
]
