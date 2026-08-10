"""Tier-1 evidence requirement — deterministic anti-confab-sottile.

The L1 keyword detectors catch HYPE confab; L3 (validate_claim) catches a
claim that CONTRADICTS an existing fact. Neither catches a *subtle* confab:
a plausible, specific FALSE claim in a NOVEL domain (an invented number, no
hype words, nothing in memory to contradict). There is no cheap way to know
it is false — but we CAN refuse to over-TRUST it.

Rule (deterministic, zero LLM, reversible): a new fact that asserts a
SPECIFIC checkable value (a quantity or a year) with NO ``verified_by``
evidence persists at ``provisional`` (status rank 1 — still recallable, just
flagged unverified) instead of ``model_claim`` (rank 2). Sourced claims,
generic claims, and explicitly-typed writes pass through unchanged.

This is the foundation under the Tier-2 LLM judge: the judge later reviews
``provisional`` specifics and promotes the corroborated ones / quarantines
the contradicted ones. Opt-in (default OFF) so the corpus-wide impact can be
measured before flipping it on — same discipline as the admission gate.
"""
from __future__ import annotations

import os

from .quantity_match import YEAR_RE, extract_quantities, numeri_ambigui

_TRUTHY = {"1", "true", "yes", "on"}

# Trust ceiling for a specific, unsourced claim. Below the typical 0.85–0.9
# of an ordinary write → it ranks under sourced/corroborated facts and reads
# as "unverified" until the Tier-2 judge (or a human) confirms it.
UNSOURCED_SPECIFIC_CEILING = 0.6


def is_specific_claim(proposition: str) -> bool:
    """True iff the text asserts a checkable specific — a quantity
    (number + unit, identifier digits excluded by the anchor) or a year.

    Generic claims ("the system is fast") have nothing concrete to be wrong
    about, so they are NOT specific and are left untouched.

    ⚠️ UN NUMERO CHE NON SI PUO' MISURARE RESTA UN'AFFERMAZIONE SPECIFICA, ed e'
    la seconda strada qui sotto. «Lo stipendio annuo e' 45.000 euro» risultava
    GENERICO — nella stessa categoria di «il sistema e' veloce», cioe' fra le
    frasi che non hanno niente di concreto su cui poter sbagliare — perche'
    ``extract_quantities`` tace sui numeri ambigui (il punto e' separatore
    decimale in una lingua e delle migliaia in un'altra, e le due letture
    differiscono di mille volte). Misurato prima della cura::

        False  <- Lo stipendio annuo e' 45.000 euro.
        True   <- Lo stipendio annuo e' 45000 euro.

    🔑 Il silenzio dell'estrattore vuol dire «non so QUANTO», non «non c'e'
    niente da verificare» — e questa funzione chiede la seconda cosa. Chi
    scrive un numero all'europea sfuggiva al requisito di evidenza proprio
    perche' il suo numero era meno verificabile, non piu'.
    """
    text = proposition or ""
    if extract_quantities(text):
        return True
    if numeri_ambigui(text):
        return True
    if YEAR_RE.search(text):
        return True
    return False


def evidence_requirement_enabled() -> bool:
    """Opt-in via ``ENGRAM_EVIDENCE_REQUIREMENT`` (default OFF)."""
    return os.environ.get(
        "ENGRAM_EVIDENCE_REQUIREMENT", "",
    ).strip().lower() in _TRUTHY


def resolve_write_confidence(
    proposition: str,
    verified_by,
    *,
    requested_confidence: float,
    enabled: bool | None = None,
    ceiling: float = UNSOURCED_SPECIFIC_CEILING,
) -> float:
    """Cap confidence for a SPECIFIC, UNSOURCED claim.

    Why confidence and not status: ``provisional`` is reserved by the store
    layer for URL/arxiv-backed hypotheses (it demotes a ref-less provisional
    back to model_claim), and adding a new status touches the whole trust
    ladder. Confidence is the natural, continuous trust dial that recall
    already ranks by — lowering it makes an unsourced specific claim rank
    below sourced/corroborated facts and read as "unverified".

    Caps ONLY when: enabled, NO ``verified_by``, the claim is specific
    (:func:`is_specific_claim`), and the requested confidence is above the
    ceiling. Everything else passes through unchanged — the rule only ever
    *withholds* trust, never raises it. (The Tier-2 judge or a human raises
    it later for corroborated claims.)
    """
    if enabled is None:
        enabled = evidence_requirement_enabled()
    if (
        enabled
        and not verified_by
        and is_specific_claim(proposition)
        and float(requested_confidence) > ceiling
    ):
        return ceiling
    return float(requested_confidence)


__all__ = [
    "is_specific_claim",
    "evidence_requirement_enabled",
    "resolve_write_confidence",
    "UNSOURCED_SPECIFIC_CEILING",
]
