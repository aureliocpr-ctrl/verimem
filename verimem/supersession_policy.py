"""Evolution-vs-conflict policy for the write path (task #48 core).

The contradiction judge (lexical L3 / NLI L3-semantic) only tells us *that* a new write
clashes with a stored fact. What to DO about it depends on provenance + time:

  * the SAME source restating its own claim with a newer value is an **evolution** —
    the world changed and the old value should be superseded (keeping both is how a
    memory serves a stale, "confabulated" answer at recall time);
  * a DIFFERENT source disagreeing is a **conflict** — a real dispute; never auto-retire
    either side on the strength of a mere timestamp.

This is deterministic (canonical source + assertion time), independent of the NLI
model's temporal reasoning — which the local cross-encoder does NOT have (measured
2026-07-19: it flags a same-source value change as a contradiction). Pure and
observation-only; it decides a LABEL, it does not mutate anything.
"""
from __future__ import annotations

from typing import Any

from .source_trust import canonical_source

__all__ = ["canonical_source_of", "is_same_source", "classify_write_relation"]


def canonical_source_of(fact: Any) -> str:
    """The reputation key of a fact's writer (``canonical_source`` of its
    ``verified_by``); the ``"user"`` fallback when unsourced."""
    return canonical_source(getattr(fact, "verified_by", None) or None)


def is_same_source(a: Any, b: Any) -> bool:
    return canonical_source_of(a) == canonical_source_of(b)


def _created(fact: Any) -> float | None:
    v = getattr(fact, "created_at", None)
    if isinstance(v, bool):  # guard: bool is an int subclass
        return None
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(v)  # numeric-looking string
    except (TypeError, ValueError):
        return None


def classify_write_relation(new_fact: Any, old_fact: Any) -> str:
    """``"evolution"`` iff ``new_fact`` is the SAME canonical source as ``old_fact`` and
    strictly NEWER (its own value updated over time); otherwise ``"conflict"`` — a
    different source, or no clear time order. Conservative: any ambiguity → conflict, so
    a fact is never auto-retired unless it is the same source superseding itself.

    SECURITY — DO NOT wire this into an ENFORCE path (auto-supersede/quarantine) without
    first gating on an AUTHENTICATED source (opus critic, 2026-07-19). Two reasons this
    verdict is safe for OBSERVE only, not yet for enforce: (1) ``verified_by`` is
    caller-controlled and spoofable, so an attacker can present a victim's canonical
    source; (2) unsourced writes all collapse to the ``"user"`` fallback, so distinct
    writers share one source bucket. And "strictly newer" is NOT an anti-spoof defense —
    on the live write path the candidate's ``created_at`` is always *now*, so the whole
    decision reduces to "same canonical source". The real discriminator must therefore be
    source AUTHENTICATION (a capability token / signed source), added in task #48 BEFORE
    evolution→supersede acts on anything."""
    if not is_same_source(new_fact, old_fact):
        return "conflict"
    tn, to = _created(new_fact), _created(old_fact)
    if tn is None or to is None or tn <= to:
        return "conflict"
    return "evolution"
