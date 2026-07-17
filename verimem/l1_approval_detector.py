"""Cycle 2026-05-27 (round 8) — L1.16 approval/sign-off claim detector.

Claude architectural choice round 8: claim "approved/signed-off/
authorized" senza evidence formal approval. Ortogonal a tutti detector
esistenti (business-process, non technical).

Patterns:
- English: approved, sign-off, signed-off, authorized, blessed, ratified
- Italian: approvato, approvata, autorizzato, ratificato, firmato

Evidence accepted:
- approval:<id>_signed or approver:<name>_signed
- review:<id>_approved (overlap minor con L1.13 ma valid)
- pr:<n>_approved
- ticket:<id>_approved
- email:<from>_approval or chat:<channel>_approved
"""
from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

_APPROVAL_PATTERN = re.compile(
    r"\b(?:approved|sign[- ]off|signed[- ]off|"
    r"authorized|authorised|blessed|ratified|"
    r"approvato|approvata|approvati|approvate|"
    r"autorizzato|autorizzata|"
    r"ratificato|ratificata|"
    r"firmato|firmata)\b",
    re.IGNORECASE,
)

_APPROVAL_EVIDENCE_PREFIXES: tuple[str, ...] = (
    "approval:", "approver:",
    "review:", "pr:", "mr:",
    "ticket:", "jira:",
    "email:", "chat:",
    "signoff:", "sign_off:",
)


@dataclass(frozen=True)
class ApprovalClaimWarning:
    matched_text: str
    advice: str


# FIX 2026-06-09 (audit#3): a bare approval prefix is NOT evidence of approval.
# 'approval:pending' / 'review:requested' / 'pr:open' used to suppress the
# warning. Require an approval OUTCOME token in the ref PAYLOAD (the part after
# the prefix, so the prefix word itself doesn't count), matched per-token.
_APPROVAL_OUTCOME_TOKENS: frozenset[str] = frozenset({
    "approved", "approval", "signed", "signoff", "sign", "ratified",
    "granted", "accepted", "merged", "authorized", "lgtm", "ack",
    "acked", "blessed", "approve",
})


def _has_approval_evidence(verified_by: Iterable[str] | None) -> bool:
    if not verified_by:
        return False
    for ref in verified_by:
        if not isinstance(ref, str):
            continue
        lower = ref.lower()
        if not any(lower.startswith(p) for p in _APPROVAL_EVIDENCE_PREFIXES):
            continue
        payload = lower.split(":", 1)[1] if ":" in lower else ""
        if any(t in _APPROVAL_OUTCOME_TOKENS
               for t in re.split(r"[^a-z0-9]+", payload)):
            return True
    return False


def detect_unsupported_approval_claim(
    *,
    proposition: str,
    verified_by: Iterable[str] | None,
) -> ApprovalClaimWarning | None:
    if not proposition:
        return None
    m = _APPROVAL_PATTERN.search(proposition)
    if m is None:
        return None
    matched_text = m.group(0)
    if _has_approval_evidence(verified_by):
        return None
    return ApprovalClaimWarning(
        matched_text=matched_text,
        advice=(
            f"Proposition contains approval claim {matched_text!r} but "
            f"no approval evidence in verified_by. Add at least one of: "
            f"approval:<id>_signed, review:<id>_approved, "
            f"pr:<n>_approved, ticket:<id>_approved, "
            f"email:<from>_approval, chat:<channel>_approved."
        ),
    )


__all__ = ["ApprovalClaimWarning", "detect_unsupported_approval_claim"]
