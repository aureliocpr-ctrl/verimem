"""Cycle 2026-05-27 (round 7) — L1.15 tested/verified detector.

Ortogonal a L1.10 (works/funziona) — L1.15 cattura claim su TESTING
process completion, non runtime behavior. Esempio:
- L1.10 fires: "Il sistema funziona" (runtime claim)
- L1.15 fires: "Tutto testato" (process claim sin pytest ref)

Patterns coperti (testing claim):
- English: tested, well-tested, verified, validated
- Italian: testato, testati, verificato, verificata, validato

Evidence accepted:
- pytest:<test>_PASS
- test_coverage:<percent>
- ci:<pipeline>:green
- review:<id>_approved
- qa:<scenario>_PASS
"""
from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

_TESTED_PATTERN = re.compile(
    r"\b(?:tested|well[- ]tested|"
    r"verified|validated|"
    r"testato|testati|testata|testate|"
    r"verificato|verificata|verificati|verificate|"
    r"validato|validata|validati|validate)\b",
    re.IGNORECASE,
)

# FIX 2026-06-03 (sorella red-team, buco L1-tested-bypass): i prefissi che
# implicano un test/processo eseguito NON bastano da soli — un ref-spazzatura
# tipo ``test:foo`` / ``pytest:run_42`` / ``ci:main`` / ``qa:x`` / ``review:y``
# passava come evidenza valida (substring ``startswith``), bypassando L1.15.
# Allineato al fix gemello di l1_works_detector (SCAN-68/NONNA): si esige un
# TOKEN di ESITO confrontato PER-TOKEN (split su non-alfanumerico), non
# substring. La metrica ``coverage`` esige invece un valore NUMERICO.
_OUTCOME_TOKENS: frozenset[str] = frozenset(
    {"pass", "passed", "passing", "green", "approved", "ok", "exit0"}
)
#: Prefissi "processo eseguito": richiedono un token di esito verificabile.
_OUTCOME_REQUIRED_PREFIXES: tuple[str, ...] = (
    "pytest:", "test:", "ci:", "qa:", "review:", "validation:",
)
#: Prefissi metrica: richiedono almeno un token numerico (es. coverage 85%).
_COVERAGE_PREFIXES: tuple[str, ...] = ("test_coverage:", "coverage:")


@dataclass(frozen=True)
class VerificationClaimWarning:
    matched_text: str
    advice: str


def _has_tested_evidence(verified_by: Iterable[str] | None) -> bool:
    """True solo se ``verified_by`` contiene un ref di test VERIFICABILE.

    Un prefisso nudo (``test:foo``) non basta: per i prefissi "processo
    eseguito" serve un token di esito (pass/green/approved/...); per i
    prefissi metrica serve un valore numerico. Confronto PER-TOKEN (non
    substring), cosi' ``test:greenfield`` / ``review:approvable_pending``
    non contano per via di una sottostringa accidentale.
    """
    if not verified_by:
        return False
    for ref in verified_by:
        if not isinstance(ref, str):
            continue
        lower = ref.lower()
        tokens = re.split(r"[^a-z0-9]+", lower)
        # Metrica coverage: serve un valore numerico (es. '85').
        if lower.startswith(_COVERAGE_PREFIXES):
            if any(t.isdigit() for t in tokens):
                return True
            continue
        # Processo eseguito: serve un token di esito verificabile.
        if lower.startswith(_OUTCOME_REQUIRED_PREFIXES):
            if any(t in _OUTCOME_TOKENS for t in tokens):
                return True
            continue
    return False


def detect_unsupported_tested_claim(
    *,
    proposition: str,
    verified_by: Iterable[str] | None,
) -> VerificationClaimWarning | None:
    if not proposition:
        return None
    m = _TESTED_PATTERN.search(proposition)
    if m is None:
        return None
    matched_text = m.group(0)
    if _has_tested_evidence(verified_by):
        return None
    return VerificationClaimWarning(
        matched_text=matched_text,
        advice=(
            f"Proposition contains tested/verified claim {matched_text!r} "
            f"but no test evidence in verified_by. Add at least one of: "
            f"pytest:<test>_PASS, test_coverage:<N>%, ci:<id>:green, "
            f"review:<id>_approved, qa:<scenario>_PASS."
        ),
    )


__all__ = ["VerificationClaimWarning", "detect_unsupported_tested_claim"]
