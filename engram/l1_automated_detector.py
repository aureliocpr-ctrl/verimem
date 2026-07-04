"""Cycle 2026-05-27 (round 10) — L1.18 automated/scheduled claim detector.

Pattern claim "automated/scheduled" senza cron/scheduler evidence reale.

Patterns:
- English: automated, automatic, scheduled, periodic, recurring
- Italian: automatizzato, programmato, schedulato, periodico

Evidence accepted:
- cron:<schedule> or schedule:<id>
- scheduler:<job_id> or trigger:<event>
- ci:<pipeline>:nightly or ci:<id>:cron
- workflow:<id>_active
- task_scheduler:<task>
"""
from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

from .l1_evidence import ref_is_negated as _ref_is_negated

_AUTOMATED_PATTERN = re.compile(
    r"\b(?:automated|automatic|automatically|"
    r"scheduled|periodic|recurring|"
    r"automatizzato|automatizzata|"
    r"programmato|programmata|"
    r"schedulato|schedulata|"
    r"periodico|periodica)\b",
    re.IGNORECASE,
)

_AUTOMATED_EVIDENCE_PREFIXES: tuple[str, ...] = (
    "cron:", "schedule:", "scheduler:",
    "trigger:", "workflow:", "task_scheduler:",
    "systemd:", "launchd:", "ci:",
    "airflow:", "celery:",
)

# 2026-06-14 FP fix: "recurring/periodic <problem-noun>" describes a problem that
# keeps happening (a recurring bug/hang/block), NOT a claim that something runs
# on a schedule. Flagging it quarantined real fix-knowledge (the 'recurring
# recall block' dogfood). Only 'recurring'/'periodic' get this descriptive pass —
# 'scheduled'/'automated' are claims of active automation and still flag.
_PROBLEM_NOUNS = (
    r"bug|bugs|hang|hangs|block|blocker|blocks|issue|issues|problem|problems|"
    r"error|errore|errors|failure|failures|crash|crashes|pattern|regression|"
    r"leak|race|deadlock|timeout|theme|defect|loss|fault|glitch|stall|freeze"
)
_DESCRIPTIVE_RECURRENCE = re.compile(
    rf"\b(?:recurring|periodic|periodico|periodica)\b(?:\W+\w+){{0,2}}\W+"
    rf"(?:{_PROBLEM_NOUNS})\b"
    rf"|\b(?:{_PROBLEM_NOUNS})\b(?:\W+\w+){{0,2}}\W+"
    rf"(?:recurring|periodic|periodico|periodica)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class AutomationClaimWarning:
    matched_text: str
    advice: str


def _has_automated_evidence(verified_by: Iterable[str] | None) -> bool:
    if not verified_by:
        return False
    for ref in verified_by:
        if not isinstance(ref, str):
            continue
        lower = ref.lower()
        # FIX 2026-06-09 (audit#3): 'cron:someday' / 'schedule:planned' do not
        # prove automation. Reject refs whose payload is a not-done modifier;
        # real schedule exprs ('cron:0_2_*_*_*') and named jobs stay valid.
        if _ref_is_negated(ref):
            continue
        if any(lower.startswith(p) for p in _AUTOMATED_EVIDENCE_PREFIXES):
            return True
    return False


def _is_descriptive_occurrence(proposition: str, m: re.Match[str]) -> bool:
    """True iff THIS specific automation keyword is a descriptive recurring
    PROBLEM (recurring/periodic next to a problem-noun), not a scheduling claim.

    Critic counterexample 2026-06-14: checking ``_DESCRIPTIVE_RECURRENCE`` against
    the WHOLE proposition let "scheduled job to catch the recurring crash" slip —
    a real automation claim co-occurring with a recurring-problem phrase. So the
    pass is decided PER keyword and only for recurring/periodic: 'scheduled' /
    'automated' never qualify, and we look only at a window around this match.
    """
    word = m.group(0).lower()
    if word not in ("recurring", "periodic", "periodico", "periodica"):
        return False
    lo = max(0, m.start() - 48)
    hi = min(len(proposition), m.end() + 48)
    return bool(_DESCRIPTIVE_RECURRENCE.search(proposition[lo:hi]))


def detect_unsupported_automated_claim(
    *,
    proposition: str,
    verified_by: Iterable[str] | None,
) -> AutomationClaimWarning | None:
    if not proposition:
        return None
    if _has_automated_evidence(verified_by):
        return None
    # Evaluate EACH automation keyword independently: skip a descriptive
    # recurring-problem occurrence, but flag the FIRST genuine claim
    # ('scheduled'/'automated', or recurring/periodic NOT next to a problem-noun).
    matched_text: str | None = None
    for m in _AUTOMATED_PATTERN.finditer(proposition):
        if _is_descriptive_occurrence(proposition, m):
            continue
        matched_text = m.group(0)
        break
    if matched_text is None:
        return None
    return AutomationClaimWarning(
        matched_text=matched_text,
        advice=(
            f"Proposition contains automation claim {matched_text!r} but "
            f"no scheduler evidence in verified_by. Add at least one of: "
            f"cron:<schedule>, schedule:<id>, scheduler:<job>, "
            f"trigger:<event>, workflow:<id>, systemd:<unit>, "
            f"airflow:<dag>, celery:<task>."
        ),
    )


__all__ = ["AutomationClaimWarning", "detect_unsupported_automated_claim"]
