"""Provenance signing on the write-path — the SMSR-complement to the truth gate.

SMSR (arXiv 2606.12703) Theorem 1, via the cortex research bridge: no
deterministic provenance-FREE filter certifies safety against an adaptive
multi-session adversary — a content gate alone can be probed and steered.
The complement is an UNFORGEABLE claim of WHO is speaking: an HMAC over
(ref body, proposition) carried INSIDE the verified_by ref itself:

    source-doc:alice:t1#sig=<hmac-sha256-hex16>

Design choices, deliberate:
  * zero schema change — the signature travels in the ref string; the
    existing ``canonical_source`` regex is untouched (it matches up to the
    first colon group, the ``#sig=`` tail never reaches it);
  * the proposition is INSIDE the MAC — a valid signature moved onto a
    different fact fails (no cut-and-paste replay across facts);
  * ``actor:*`` refs are EXEMPT here: engine self-writes are governed by P85
    (they never testify), not by source signing;
  * key from ``VERIMEM_PROVENANCE_KEY`` (legacy ``ENGRAM_PROVENANCE_KEY`` still
    honoured); with no key the layer is INERT and nothing changes.

Wiring (2026-07-27): the write path now CONSULTS this module — ``store()`` calls
``signature_offenders`` and quarantines a write whose refs claim a signature that
does not verify. Until that date the module had zero call sites, so the "opt-in"
the docs advertised could not be opted into: setting the key was inert. What is
refused is narrow on purpose — an UNSIGNED ref is still fine (historical
provenance is unsigned; refusing it would quarantine the corpus), and only a
BROKEN signature is treated as forgery.

Honest scope: this authenticates the WRITER'S CHANNEL, not the truth of the
source document itself — that is the truth-gate's job. Both together are the
SMSR composition: what is said (entailment) + who says it (signature).
"""
from __future__ import annotations

import hashlib
import hmac
import os
from typing import Any

from .self_provenance import is_self_ref

__all__ = ["audit_store", "provenance_key", "sign_ref", "signature_offenders",
           "verify_fact_refs", "verify_ref"]

_SIG_TAG = "#sig="
_SIG_LEN = 16          # hex chars — 64 bits of MAC, plenty for a write channel


def provenance_key() -> str | None:
    """``VERIMEM_PROVENANCE_KEY`` — None means signing is not configured.

    ``ENGRAM_PROVENANCE_KEY`` stays honoured as the legacy spelling (it is what
    every existing deployment sets); the verimem name wins when both are set.
    """
    key = os.environ.get("VERIMEM_PROVENANCE_KEY", "").strip()
    if not key:
        key = os.environ.get("ENGRAM_PROVENANCE_KEY", "").strip()
    return key or None


def signature_offenders(fact: Any) -> list[str]:
    """The refs on ``fact`` that CLAIM a signature and fail to back it.

    Empty when signing is unconfigured (the layer is inert), when no ref carries
    the ``#sig=`` tag, or when every signature verifies. ``actor:`` refs are
    exempt — P85 admits engine writes by verification, never by claimed origin.

    This is the read side of the wiring: an unsigned ref is NOT an offender
    (historical provenance is unsigned and must keep working), but a signature
    that does not verify is — someone asserted an origin and the assertion does
    not hold, which is exactly the forgery this module exists to catch.
    """
    key = provenance_key()
    if not key:
        return []
    proposition = (getattr(fact, "proposition", "") or "").strip()
    offenders: list[str] = []
    for ref in getattr(fact, "verified_by", None) or []:
        if not isinstance(ref, str) or _SIG_TAG not in ref:
            continue
        if is_self_ref(ref):        # same exemption test as verify_fact_refs
            continue
        if not verify_ref(ref, proposition, key=key):
            offenders.append(ref)
    return offenders


def _mac(body: str, proposition: str, key: str) -> str:
    msg = f"{body}\x1f{proposition}".encode()
    return hmac.new(key.encode("utf-8"), msg, hashlib.sha256).hexdigest()[:_SIG_LEN]


def sign_ref(ref: str, proposition: str, *, key: str) -> str:
    """Attach the channel signature to a provenance ref. The proposition is
    part of the MAC — the signature cannot be replayed onto another fact."""
    body = ref.split(_SIG_TAG, 1)[0]
    return f"{body}{_SIG_TAG}{_mac(body, proposition, key)}"


def verify_ref(ref: str, proposition: str, *, key: str) -> bool:
    """True iff ``ref`` carries a signature valid for this proposition+key.
    An unsigned ref is False (verification asks 'is this proven authentic?',
    not 'is this suspicious?')."""
    if _SIG_TAG not in (ref or ""):
        return False
    body, sig = ref.split(_SIG_TAG, 1)
    return hmac.compare_digest(sig, _mac(body, proposition, key))


def verify_fact_refs(fact: Any, *, key: str) -> dict[str, Any]:
    """Audit one fact's refs: ``{signed, unsigned, invalid, exempt, ok}``.
    ``ok`` = every non-exempt ref carries a VALID signature. ``actor:*`` refs
    are exempt (P85 governs them); a ref with a BROKEN signature counts as
    invalid, worse than unsigned."""
    signed = unsigned = invalid = exempt = 0
    prop = getattr(fact, "proposition", "") or ""
    for ref in (getattr(fact, "verified_by", None) or []):
        if not isinstance(ref, str):
            continue
        if is_self_ref(ref):
            exempt += 1
        elif _SIG_TAG not in ref:
            unsigned += 1
        elif verify_ref(ref, prop, key=key):
            signed += 1
        else:
            invalid += 1
    return {"signed": signed, "unsigned": unsigned, "invalid": invalid,
            "exempt": exempt, "ok": unsigned == 0 and invalid == 0}


def audit_store(semantic: Any, *, key: str,
                limit: int = 10000) -> dict[str, Any]:
    """Walk the live store and report signature coverage — the deployment
    readiness check before flipping enforcement on. Names the offenders
    (near-misses discipline: ids, not 'issues were found')."""
    checked = fully = 0
    offenders: list[str] = []
    invalid_ids: list[str] = []
    for fact in semantic.all()[:limit]:
        if fact.superseded_by or fact.status in ("quarantined", "orphaned"):
            continue
        if not (fact.verified_by or []):
            continue
        checked += 1
        rep = verify_fact_refs(fact, key=key)
        if rep["ok"]:
            fully += 1
        else:
            offenders.append(fact.id)
            if rep["invalid"]:
                invalid_ids.append(fact.id)
    return {"facts_checked": checked, "fully_signed": fully,
            "offender_ids": offenders, "invalid_sig_ids": invalid_ids,
            "coverage": (fully / checked) if checked else 0.0}
