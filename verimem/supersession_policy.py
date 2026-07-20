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


def _coerce_ts(v: Any) -> float | None:
    if isinstance(v, bool):  # guard: bool is an int subclass
        return None
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(v)  # numeric-looking string
    except (TypeError, ValueError):
        return None


def _when_true(fact: Any) -> float | None:
    """WHEN the fact is asserted TRUE — ``asserted_at`` (bi-temporal valid-time) when
    present, else ``created_at`` (write-time). Valid-time is what must order an
    evolution: the candidate's write-time is always *now*, so ordering by write-time
    alone would call a BACKFILL (re-asserting an OLD value) a newer 'evolution' and
    retire the current value (opus critic, 2026-07-19)."""
    for attr in ("asserted_at", "created_at"):
        t = _coerce_ts(getattr(fact, attr, None))
        if t is not None:
            return t
    return None


def classify_write_relation(new_fact: Any, old_fact: Any) -> str:
    """``"evolution"`` iff ``new_fact`` is the SAME canonical source as ``old_fact`` and
    strictly NEWER in VALID-TIME (``asserted_at`` when present, else ``created_at``);
    otherwise ``"conflict"`` — a different source, or no clear time order. Conservative:
    any ambiguity → conflict, so a fact is never auto-retired unless it is the same source
    superseding itself with a later valid-time.

    SECURITY — the enforce wiring (``ENGRAM_SUPERSEDE_SAME_SOURCE``, task #48) has NO
    source authentication, and this function provides NONE. ``verified_by`` is
    caller-controlled and spoofable (even the ``actor:`` self-provenance prefix is a bare
    string), and unsourced writes collapse to the ``"user"`` bucket, so a same-source
    verdict is only as trustworthy as the writers in a tenant. What actually makes enforce
    safe is therefore NOT authentication (unbuilt) but: (a) the TENANCY isolation boundary
    (cross-tenant writes are already blocked); (b) a single-agent-per-tenant assumption
    (the sole agent superseding its OWN values is the intended feature). A
    multi-agent-per-tenant deployment enabling it accepts intra-tenant griefing (the
    unbuilt per-agent-auth gap). Cross-source clashes never reach the supersede path
    (they classify as ``"conflict"``).

    CORRECTED 2026-07-20 (independent red-team audit): this docstring still claimed
    "it is DEFAULT-OFF — a knowing opt-in" as safety argument (a). That was STALE — the
    default flipped to **ON** on 2026-07-19 (``anti_confab_gate._supersede_same_source_on``,
    ``ENGRAM_SUPERSEDE_SAME_SOURCE`` defaults to "1"). A reader was being told the guard
    rested on an opt-in that no longer exists.

    OPEN RISK, not yet decided: assumption (b) is exactly what the architecture-A thin
    tier breaks. N agent sessions behind ONE shared server share ONE tenant key, so
    "single agent per tenant" is false by construction there, and one compromised session
    can retire another's true values. Until per-writer auth ships, a shared-server
    deployment that cannot trust every session should set
    ``ENGRAM_SUPERSEDE_SAME_SOURCE=0``."""
    if not is_same_source(new_fact, old_fact):
        return "conflict"
    tn, to = _when_true(new_fact), _when_true(old_fact)
    if tn is None or to is None or tn <= to:
        return "conflict"
    return "evolution"
