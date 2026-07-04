"""Cycle 2026-05-27 (round 4) — L1.12 security/hardened claim detector.

Triangulation Claude+Gemini+GPT entrambi votano (d) secure/hardened
come L1.12 priority. Motivo: distinto da L1.10 works e L1.11 production-
ready perche induce 'falsa sicurezza operativa'. Hardening e' attivita
post-deployment distinct.

Patterns coperti (security claim):
- English: secure, secured, hardened, hardening, security-ready,
  tamper-proof, vulnerability, CVE-
- Italian: sicuro, messo in sicurezza, blindato

Evidence accepted (security validation):
- audit:<...> or security_audit:<...>_PASS
- pentest:<...>_PASS
- threat_model:<id>_reviewed or threat-model:
- bandit:<...>_PASS or semgrep:<...>_PASS
- vuln_scan:<...>_PASS or dependency_scan:<...>_PASS
- npm_audit:<...>_PASS
- audit-trail:<id> (Gemini-proposed)

Closes A2 ANTI-HALL gap per claim sicurezza (no audit = no claim valid).
"""
from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

# Security claim patterns
_SECURITY_PATTERN = re.compile(
    r"\b(?:secure|secured|hardened|hardening|"
    r"security[- ]?ready|tamper[- ]?proof|"
    r"sicuro|blindato|"
    r"messo in sicurezza|"
    r"vulnerability|CVE-\d+)\b",
    re.IGNORECASE,
)

# FIX 2026-06-09 (audit#3): a bare security prefix is NOT evidence. The
# process-executed checks need a verifiable OUTCOME token (per-token, not
# substring) — 'audit:planned_next_quarter' / 'pentest:scheduled' used to
# suppress the warning. Artifact refs (a threat-model id / audit trail) are
# the evidence themselves, so they stay bare-accepted.
_SECURITY_PROCESS_PREFIXES: tuple[str, ...] = (
    "audit:", "security_audit:", "security-audit:",
    "pentest:", "bandit:", "semgrep:",
    "vuln_scan:", "vuln-scan:",
    "dependency_scan:", "dependency-scan:",
    "npm_audit:", "npm-audit:",
)
_SECURITY_OUTCOME_TOKENS: frozenset[str] = frozenset({
    "pass", "passed", "passing", "clean", "reviewed", "ok", "green",
    "none", "0",
})
_SECURITY_ARTIFACT_PREFIXES: tuple[str, ...] = (
    "threat_model:", "threat-model:", "audit-trail:", "audit_trail:",
)


@dataclass(frozen=True)
class SecurityClaimWarning:
    """Warning emitted when 'secure/hardened' claim lacks audit evidence."""

    matched_text: str
    advice: str


def _has_security_evidence(verified_by: Iterable[str] | None) -> bool:
    """Return True iff verified_by contains security validation evidence.

    Process-executed checks (audit/pentest/bandit/semgrep/vuln_scan/...) need a
    verifiable OUTCOME token (pass/clean/reviewed/...), compared PER-TOKEN; a
    bare prefix like 'audit:planned' is NOT evidence. Artifact refs
    (threat_model:/audit-trail:) are accepted bare — the ref IS the artifact.
    """
    if not verified_by:
        return False
    for ref in verified_by:
        if not isinstance(ref, str):
            continue
        lower = ref.lower()
        if lower.startswith(_SECURITY_ARTIFACT_PREFIXES):
            return True
        if lower.startswith(_SECURITY_PROCESS_PREFIXES):
            tokens = re.split(r"[^a-z0-9]+", lower)
            if any(t in _SECURITY_OUTCOME_TOKENS for t in tokens):
                return True
            continue
    return False


def detect_unsupported_security_claim(
    *,
    proposition: str,
    verified_by: Iterable[str] | None,
) -> SecurityClaimWarning | None:
    """Return Warning if proposition contains 'secure/hardened' claim
    AND verified_by lacks security audit evidence. Else None.
    """
    if not proposition:
        return None
    m = _SECURITY_PATTERN.search(proposition)
    if m is None:
        return None
    matched_text = m.group(0)
    if _has_security_evidence(verified_by):
        return None
    return SecurityClaimWarning(
        matched_text=matched_text,
        advice=(
            f"Proposition contains security claim {matched_text!r} but "
            f"no audit evidence in verified_by. Add at least one of: "
            f"audit:<id>, security_audit:<id>_PASS, pentest:<id>_PASS, "
            f"threat_model:<id>_reviewed, bandit:<r>_PASS, "
            f"semgrep:<r>_PASS, vuln_scan:<r>_PASS, "
            f"dependency_scan:<r>_PASS."
        ),
    )


__all__ = [
    "SecurityClaimWarning",
    "detect_unsupported_security_claim",
]
