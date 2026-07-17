"""Cycle 2026-05-27 (round 3) — L1.11 production-ready/stable detector.

Aurelio mandate 2026-05-27: prevent "production-ready/stable" claims
without coverage/soak/release evidence — claim "business-grade" ad alto
rischio, spesso abusato dopo solo test locali verdi.

Triangulation Claude+Gemini+GPT 2026-05-27 round 3:
- Gemini: regex `\b(production-ready|stable)\b`, evidence `release-tag:`
- GPT: regex piu ricco con prod-ready/ship-ready/robust + evidence
  coverage/soak/CI green/regression PASS
- Convergenza 2/2 su (b) production-ready/stable

Patterns coperti (claim "maturita"):
- production-ready / prod-ready / production ready
- ship-ready / release-ready
- stable / stabile / robusto / robust
- enterprise-grade / business-grade / battle-tested

Evidence accepted (claim "validazione formale"):
- coverage:<percent> with >=N% threshold
- soak:<duration> (soak test marker)
- stress:<test> (stress test)
- regression:<status>_PASS
- ci:<pipeline>:green
- release_tag:<version>
- pytest:<test>_PASS

Closes A2 ANTI-HALL + A4 NO MARKETING gap (claim "production-ready"
senza evidenza formale = marketing).
"""
from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

# Production-ready claim patterns
_PROD_READY_PATTERN = re.compile(
    r"\b(?:production[- ]?ready|prod[- ]?ready|production ready|"
    r"ship[- ]?ready|release[- ]?ready|"
    r"stable|stabile|robust|robusto|"
    r"enterprise[- ]?grade|business[- ]?grade|"
    r"battle[- ]?tested)\b",
    re.IGNORECASE,
)

# Evidence prefixes that count as "validation formale"
_PROD_EVIDENCE_PREFIXES: tuple[str, ...] = (
    "coverage:", "soak:", "stress:",
    "regression:", "ci:", "release_tag:",
    "release-tag:", "pytest:",
)


@dataclass(frozen=True)
class ProdReadyClaimWarning:
    """Warning emitted when 'production-ready/stable' claim lacks
    formal validation evidence."""

    matched_text: str
    advice: str


def _has_prod_evidence(verified_by: Iterable[str] | None) -> bool:
    """Return True iff verified_by contains formal validation evidence."""
    if not verified_by:
        return False
    for ref in verified_by:
        if not isinstance(ref, str):
            continue
        lower = ref.lower()
        # FIX 2026-06-03 (sorella red-team, buco L1.11-substring): l'esito di
        # ci:/pytest: era confrontato come SUBSTRING ('ci:passenger' conteneva
        # 'pass', 'pytest:compass' conteneva 'pass') → evidenza-spazzatura
        # accettata. Allineato a l1_works_detector.py: confronto PER-TOKEN
        # (split su non-alfanumerico). I bare-prefix (soak/stress/regression/
        # release_tag) restano accettati by-design (il ref È la prova).
        toks = re.split(r"[^a-z0-9]+", lower)
        # coverage:<N>% — accept ONLY with an explicit numeric percentage.
        # FIX 2026-06-09 (audit#3): bare 'coverage:planned'/'coverage:tbd' was
        # accepted as formal validation (the ci:/pytest: branches were
        # token-hardened on 2026-06-03 but coverage: was left bare). Require a
        # digit, matching l1_tested_detector.py.
        if lower.startswith("coverage:"):
            if any(t.isdigit() for t in toks):
                return True
            continue
        # soak/stress/regression with test/PASS marker
        if any(lower.startswith(p) for p in
               ("soak:", "stress:", "regression:")):
            return True
        # ci:<pipeline>:green or ci:<pipeline>_PASS — token di esito
        if lower.startswith("ci:") and any(
            t in ("green", "pass", "passed", "passing") for t in toks
        ):
            return True
        # release_tag: or release-tag:
        if lower.startswith("release_tag:") or lower.startswith("release-tag:"):
            return True
        # pytest:<test>_PASS — token di esito
        if lower.startswith("pytest:") and any(
            t in ("pass", "passed", "passing") for t in toks
        ):
            return True
    return False


def detect_unsupported_prod_ready_claim(
    *,
    proposition: str,
    verified_by: Iterable[str] | None,
) -> ProdReadyClaimWarning | None:
    """Return Warning if proposition contains 'production-ready/stable'
    claim AND verified_by lacks formal validation evidence. Else None.
    """
    if not proposition:
        return None
    m = _PROD_READY_PATTERN.search(proposition)
    if m is None:
        return None
    matched_text = m.group(0)
    if _has_prod_evidence(verified_by):
        return None
    return ProdReadyClaimWarning(
        matched_text=matched_text,
        advice=(
            f"Proposition contains production-ready/stable claim "
            f"{matched_text!r} but no formal validation evidence in "
            f"verified_by. Add at least one of: coverage:<N%>, "
            f"soak:<duration>, stress:<test>, regression:<id>_PASS, "
            f"ci:<pipeline>:green, release_tag:<v>, pytest:<t>_PASS."
        ),
    )


__all__ = [
    "ProdReadyClaimWarning",
    "detect_unsupported_prod_ready_claim",
]
