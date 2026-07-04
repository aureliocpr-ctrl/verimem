"""Shared evidence primitives for the L1.x anti-confabulation detectors.

FIX 2026-06-09 (audit#3, 8-agent code audit): several detectors accepted a
BARE evidence prefix (e.g. ``approval:pending``, ``alert:planned``,
``cron:someday``) as if it substantiated the claim — the 2026-06-03 per-token
hardening was applied to only some detectors (works/tested/completion/
production-ready) and skipped on security/approval/monitored/automated. A
reference whose payload is an explicit NOT-DONE modifier negates the claim and
must NOT count as evidence. Centralized here so new detectors inherit the guard
instead of re-introducing the bare-prefix hole.
"""
from __future__ import annotations

import re

#: Tokens that mark a referenced process/artifact as NOT-yet-done -> the ref
#: does not substantiate a "done" claim. Deliberately conservative: only
#: unambiguous not-done words (no 'open'/'active'/'scheduled', which are
#: legitimately present in real evidence like 'prometheus:rule_active' or
#: 'opentelemetry').
NEGATING_TOKENS: frozenset[str] = frozenset({
    "planned", "pending", "someday", "later", "tbd", "todo", "wip",
    "draft", "proposed", "requested", "manual", "manually", "notyet",
    "backlog", "wishlist", "intended", "aspirational", "wishful",
})


def _tokens(ref: str) -> list[str]:
    return re.split(r"[^a-z0-9]+", ref.lower())


def ref_is_negated(ref: str) -> bool:
    """True if the ref's payload contains an explicit not-done modifier
    (per-token) -> it must not be treated as evidence of a completed claim."""
    if not isinstance(ref, str):
        return False
    return any(t in NEGATING_TOKENS for t in _tokens(ref))


__all__ = ["NEGATING_TOKENS", "ref_is_negated"]
