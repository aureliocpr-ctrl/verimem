"""Cycle #128 (2026-05-17) — L1 anti-confabulation warning layer.

Aurelio direttiva 2026-05-17: "studiamo confabulazioni, come prevenirle
in memoria".

Empirical motivation (sessione 2026-05-17):
* 7 confabulazioni mie ammesse onestamente.
* 2/7 dirette al pattern "X SHIPPED PR #N commit_hash" — fact salvati
  pre-merge come ``status='model_claim'``, nessuna validation cycle 111
  v2 (che si applica solo a ``status='verified'``).
* Fact reali storici implicati: ``90326a635c96`` (Cycle 119 WIRE
  SHIPPED PR #61 c37fa87) + ``201dd68bb40b`` (Cycle 120 SHIPPED PR
  #62). Entrambi avevano keyword ``SHIPPED`` ma verified_by con tool
  refs generici, niente ``commit:`` / ``pr:`` / ``file:`` markers
  verificabili contro git log main.
* Conseguenza post-compact: la mia memoria al SessionStart hook diceva
  "5 cycle SHIPPED in main" → falso pre-step-A.

Design L1 (subagent #7 architect, fact ``8be6bdd34903``):

  When proposition contains keyword ∈ {SHIPPED, MERGED, WIRED, DEPLOYED}
  AND verified_by lacks commit-tracking ref (regex ``^(commit:|pr:|
  file:|git:)``), emit observability warning. The fact is STILL saved
  (no breaking change) — the warning is signal for the operator / for
  later L2 reconciler scrubbing.

Why warning (not reject)?
* Cycle 109 hard-gate is reserved for ``status='verified'``. Extending
  the gate to ``model_claim`` would break the "store a guess and revise
  later" workflow which is core to how the agent reasons.
* The warning lives in the observability bus + audit log so a future
  L2 reconciler (cycle #129+) can scan and flip stale claims to
  ``status='orphaned'``.

NOT in scope V1:
* L2 async reconciler (separate cycle, scope TBD).
* schema v6 migration with ``commit_ref`` column.
"""
from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

# Cycle #128: keywords that strongly imply a git-state claim. Upper-case
# canonical form so the check is a simple substring on .upper().
SHIPPED_KEYWORDS = frozenset({
    "SHIPPED",
    "MERGED",
    "WIRED",
    "DEPLOYED",
})

# Verified_by reference prefixes that indicate commit-traceability.
# A verified_by entry that starts with one of these is treated as a
# legitimate anchor for a SHIPPED-style claim. Other prefixes (tool:,
# agent:, url:, ...) are not sufficient.
_COMMIT_REF_RE = re.compile(r"^(commit:|file:|git:)", re.IGNORECASE)
# A pr: ref anchors a SHIPPED/MERGED/DEPLOYED claim ONLY if it carries a CLEAN,
# non-negated "merged" token. A bare / open / negated / future pr: ('pr:99',
# 'pr:99:unmerged', 'pr:99:not_merged', 'pr:7:to_be_merged', 'pr:42:awaiting_merge')
# is NOT landed — the 2026-05-17 pre-merge confabulation pattern. (A naive
# `.*merged` regex matched 'unmerged'/'not_merged' — the sincerity re-review hole.)
# Split a pr: body into separator-delimited tokens; it is landed iff a clean
# 'merged' token is present AND no negation/future qualifier is. Tokenizing (not
# a \b regex) is the robust choice: '_' is a regex word-char, so \bnot\b does NOT
# see 'not' in 'not_merged' — the second hole the sincerity re-review exposed.
_PR_TOKEN_SPLIT_RE = re.compile(r"[:_/#\s.-]+")
# Fail-safe ALLOW-list: a pr: is landed only if its 'merged' token is accompanied
# (besides the numeric/hash id) solely by KNOWN landed qualifiers. Any other token
# (almost/partially/to/be/main/...) means "not provably landed" -> warn. A
# deny-list of negations can never be exhaustive (the critic's 'almost_merged'
# hole); an allow-list fails safe — a false "needs anchor" beats a false "trusted".
_PR_LANDED_QUALIFIERS = frozenset({
    "merged", "auto", "squash", "rebase", "ff", "fastforward", "fast",
    "forward", "manually", "cleanly", "successfully", "landed",
})


def _find_shipped_keyword(proposition: str) -> str | None:
    """Return the first SHIPPED-like keyword found, else ``None``."""
    upper = (proposition or "").upper()
    for kw in SHIPPED_KEYWORDS:
        if kw in upper:
            return kw
    return None


def _is_pr_id_token(token: str) -> bool:
    """A pr id-ish token to ignore when checking qualifiers: pure digits, or a
    hex-ish hash (>=6 hex chars)."""
    if token.isdigit():
        return True
    return len(token) >= 6 and all(c in "0123456789abcdef" for c in token)


def _is_landed_pr_ref(ref: str) -> bool:
    """True only for a pr: ref provably merged: a 'merged' token is present AND
    every non-id qualifier is a KNOWN landed qualifier (auto/squash/rebase/...).
    Unknown qualifiers (almost/partially/to-be/branch names) fail safe -> warn."""
    if not ref.lower().startswith("pr:"):
        return False
    tokens = [t for t in _PR_TOKEN_SPLIT_RE.split(ref[3:].lower()) if t]
    if "merged" not in tokens:
        return False
    qualifiers = [t for t in tokens if not _is_pr_id_token(t)]
    return all(q in _PR_LANDED_QUALIFIERS for q in qualifiers)


def _has_commit_ref(verified_by: Iterable[str] | None) -> bool:
    """True if any ref is a LANDED anchor for a shipped-like claim: commit:/
    file:/git:, or a pr: that is genuinely merged. A bare/open/negated/future
    pr: does NOT anchor a SHIPPED claim (the 2026-05-17 pre-merge confab)."""
    return any(
        _COMMIT_REF_RE.match(ref or "") or _is_landed_pr_ref(ref or "")
        for ref in (verified_by or [])
    )


def detect_unsupported_shipped_claim(
    *,
    proposition: str,
    verified_by: Iterable[str] | None,
) -> str | None:
    """L1 anti-confabulation warning detector.

    Returns a human-readable warning string when:
    * ``proposition`` contains a SHIPPED-like keyword, AND
    * ``verified_by`` lacks any commit/pr/file/git reference.

    Returns ``None`` when no warning is needed.

    This is a PURE detection function — no I/O, no global state, no
    BUS emit. The caller (SemanticMemory.store) decides what to do
    with the warning (emit event, log, count, ignore).
    """
    kw = _find_shipped_keyword(proposition)
    if kw is None:
        return None
    if _has_commit_ref(verified_by):
        return None
    return (
        f"L1 anti-confabulation: proposition contains '{kw}' keyword "
        f"but verified_by lacks commit-tracking reference "
        f"(commit:|pr:|file:|git:). This pattern caused 2/7 confabulations "
        f"in session 2026-05-17 (cycle 119/120 'SHIPPED' claim pre-merge). "
        f"To anchor the claim, add a ref like 'commit:abc123def' or "
        f"'pr:99:merged' or 'file:engram/x.py:42'."
    )


# ---------------------------------------------------------------------------
# Cycle #130 (2026-05-17) — L1.5 diagnosis detector.
#
# Empirical motivation (cycle #129 replay output):
# * 3/7 confabulations of session 2026-05-17 are diagnosis-driven
#   (e.g. "Bug X is...", "fixed Y", "diagnosed Z") and were saved with
#   verified_by entries that only described the SYMPTOM, not a
#   falsifying test that proves the root cause.
# * L1 (SHIPPED keyword) does NOT cover these — coverage 0/3 for the
#   ``diagnosis`` category in cycle #129 replay.
#
# L1.5 pattern: when proposition contains a diagnosis-like keyword AND
# verified_by lacks a test-like reference (pytest:, test:, bash:, ...),
# emit a warning. Same NO-BREAKING contract as L1.
# ---------------------------------------------------------------------------

DIAGNOSIS_KEYWORDS = frozenset({
    "BUG #",       # "Bug #11 search miss"
    "BUG IDENT",   # "Bug identificato"
    "DIAGNOSED",   # "diagnosed as X"
    "ROOT CAUSE",  # "Root cause is Y"
    "ROOTCAUSE",   # variant
})

# Verified_by ref prefixes that indicate a falsifying / reproducing
# test or empirical run — strong evidence for a diagnosis claim.
_TEST_REF_RE = re.compile(
    r"^(test:|pytest:|bash:|exit:|cmd:|run:)", re.IGNORECASE,
)


def _find_diagnosis_keyword(proposition: str) -> str | None:
    """Return the first diagnosis-like keyword found, else ``None``."""
    upper = (proposition or "").upper()
    for kw in DIAGNOSIS_KEYWORDS:
        if kw in upper:
            return kw
    return None


def _has_test_ref(verified_by: Iterable[str] | None) -> bool:
    """True if any ref in ``verified_by`` matches test/pytest/bash."""
    return any(
        _TEST_REF_RE.match(ref or "")
        for ref in (verified_by or [])
    )


def detect_unsupported_diagnosis_claim(
    *,
    proposition: str,
    verified_by: Iterable[str] | None,
) -> str | None:
    """L1.5 anti-confabulation warning for diagnosis-driven claims.

    Returns a warning string when:
    * ``proposition`` contains a diagnosis-like keyword
      (BUG #, DIAGNOSED, ROOT CAUSE, ...), AND
    * ``verified_by`` lacks any test/pytest/bash reference.

    Returns ``None`` otherwise. Pure detection function, same contract
    as ``detect_unsupported_shipped_claim``.
    """
    kw = _find_diagnosis_keyword(proposition)
    if kw is None:
        return None
    if _has_test_ref(verified_by):
        return None
    return (
        f"L1.5 anti-confabulation: proposition contains '{kw}' keyword "
        f"but verified_by lacks test-like reference (test:|pytest:|"
        f"bash:|exit:|cmd:|run:). This pattern caused 3/7 confabulations "
        f"in session 2026-05-17 (symptom-driven diagnostics without "
        f"falsifying test). To anchor the claim, add a ref like "
        f"'pytest:test_x_falsifies_pre_fix' or "
        f"'bash:python -c x_actual_output:exit0'."
    )


# ---------------------------------------------------------------------------
# Cycle #131 (2026-05-17) — L1.7 task-state detector.
#
# Empirical motivation: cycle #129 replay residual gap is 1/7 (task-state
# category, confab #1 "Cycle 45 stress concurrency da chiudere") — L1
# (SHIPPED) and L1.5 (BUG #|DIAGNOSED) do NOT catch task-state claims
# like "cycle X da chiudere" / "task Y aperto" / "PR #N pending".
#
# L1.7 pattern: when proposition contains a task-state phrase AND
# verified_by lacks a tracker reference (pr:|issue:|task:|git:|commit:),
# emit a warning. Same NO-BREAKING contract as L1 / L1.5.
# ---------------------------------------------------------------------------

# Task-state phrases. Kept as a frozenset for the public contract, but the
# matching is WORD-BOUNDED regex, not bare substring — bare `in` matching made
# "is open" fire inside "hi[s open]ness" and downgraded 6/300 legitimate
# personal biographies (FLAGS-AUDIT §8 item 4, measured 2026-07-16).
TASK_STATE_PHRASES = frozenset({
    "da chiudere",
    "da aprire",
    "is closed",
    "is open",
    "is pending",
    "still pending",
    "ancora aperto",
    "ancora chiuso",
    "candidato cycle dedicato",
})

# "is open to <...>" is the personal-availability idiom ("is open to exploring
# new genres"), not a task state ("the PR is open") — excluded via lookahead.
_TASK_STATE_RE = re.compile(
    "|".join(
        rf"\b{re.escape(p)}\b(?!\s+to\b)" if p == "is open"
        else rf"\b{re.escape(p)}\b"
        for p in sorted(TASK_STATE_PHRASES)
    ),
    re.IGNORECASE,
)

# Tracker-reference prefixes that anchor a task-state claim to a
# verifiable record (open PR list, issue tracker, git ref).
_TRACKER_REF_RE = re.compile(
    r"^(pr:|issue:|task:|git:|commit:|gh:)", re.IGNORECASE,
)


def _find_task_state_phrase(proposition: str) -> str | None:
    """Return the first task-state phrase found (word-bounded), else ``None``."""
    m = _TASK_STATE_RE.search(proposition or "")
    return m.group(0).lower() if m else None


def _has_tracker_ref(verified_by: Iterable[str] | None) -> bool:
    """True if any ref in ``verified_by`` matches pr/issue/task/git."""
    return any(
        _TRACKER_REF_RE.match(ref or "")
        for ref in (verified_by or [])
    )


def detect_unsupported_task_state_claim(
    *,
    proposition: str,
    verified_by: Iterable[str] | None,
) -> str | None:
    """L1.7 anti-confabulation warning for task-state claims.

    Returns a warning string when:
    * ``proposition`` contains a task-state phrase, AND
    * ``verified_by`` lacks any tracker reference.

    Returns ``None`` otherwise.
    """
    phrase = _find_task_state_phrase(proposition)
    if phrase is None:
        return None
    if _has_tracker_ref(verified_by):
        return None
    return (
        f"L1.7 anti-confabulation: proposition contains task-state "
        f"phrase '{phrase}' but verified_by lacks tracker reference "
        f"(pr:|issue:|task:|git:|commit:|gh:). This pattern caused "
        f"1/7 confabulations in session 2026-05-17 (cycle 115.F false "
        f"flag su cycle #45 'da chiudere'). To anchor the claim, add "
        f"a ref like 'pr:#42:state=open' or 'gh:issue/12:status'."
    )


# ---------------------------------------------------------------------------
# Cycle #132 (2026-05-17) — L2 async reconciler (DETECTION-only V1).
#
# Cycle 128/130/131 (L1/L1.5/L1.7) emit a warning at WRITE time. Facts
# saved BEFORE cycle 128 in main do NOT get the warning — they live
# silently as confabulations in the corpus. L2 is the scrub layer:
# a passive scanner that walks the current corpus and identifies which
# existing facts would have triggered a warning if they were saved
# today.
#
# V1 is DETECTION-only — no mutation, no schema change. The output is
# a structured report the operator (Aurelio) can inspect via the
# scan_orphaned_facts() helper. Future cycles may add a v6 schema
# migration with an "orphaned" status enum so the reconciler can flip
# detected facts automatically.
#
# Empirical contract: the reconciler is a wrapper around the existing
# pure detectors. The same logic that guards write-time also guards
# read-time scrub. By construction, the 7 historical confabulations of
# session 2026-05-17 (covered 7/7 by L1+L1.5+L1.7) would also be
# flagged by L2 if they're already in the corpus when the scanner runs.
# ---------------------------------------------------------------------------


def scan_orphaned_facts(
    facts: Iterable[Any],
    *,
    include_shipped: bool = True,
    include_diagnosis: bool = True,
    include_task_state: bool = True,
) -> dict[str, list[tuple[str, str]]]:
    """Scan a corpus of facts and return ones that would trigger an
    anti-confabulation warning if saved today.

    Parameters
    ----------
    facts:
        Iterable of fact-like objects with attributes ``id``,
        ``proposition``, ``verified_by``. Accepts any duck-typed
        object — ``SemanticMemory.all()`` output is the canonical
        input but the reconciler is store-agnostic.
    include_shipped / include_diagnosis / include_task_state:
        Toggle which categories to scan. Default: all three.

    Returns
    -------
    Dict keyed by category (``"shipped"`` | ``"diagnosis"`` |
    ``"task_state"``). Each value is a list of ``(fact_id, warning_msg)``
    tuples. Empty lists when no orphans in that category.

    Pure function — no mutation, no I/O, no global state.
    """
    out: dict[str, list[tuple[str, str]]] = {
        "shipped": [],
        "diagnosis": [],
        "task_state": [],
    }
    for fact in facts:
        fid = getattr(fact, "id", "")
        prop = getattr(fact, "proposition", "")
        vb = list(getattr(fact, "verified_by", []) or [])
        if include_shipped:
            w = detect_unsupported_shipped_claim(
                proposition=prop, verified_by=vb,
            )
            if w is not None:
                out["shipped"].append((fid, w))
        if include_diagnosis:
            w = detect_unsupported_diagnosis_claim(
                proposition=prop, verified_by=vb,
            )
            if w is not None:
                out["diagnosis"].append((fid, w))
        if include_task_state:
            w = detect_unsupported_task_state_claim(
                proposition=prop, verified_by=vb,
            )
            if w is not None:
                out["task_state"].append((fid, w))
    return out


def summarize_scan(report: dict[str, list[tuple[str, str]]]) -> str:
    """Render a one-line summary of a ``scan_orphaned_facts`` report."""
    counts = {k: len(v) for k, v in report.items()}
    total = sum(counts.values())
    parts = ", ".join(f"{k}={v}" for k, v in counts.items() if v)
    return (
        f"L2 reconciler: {total} orphan facts found"
        + (f" ({parts})" if parts else " (corpus clean)")
    )


__all__ = [
    "SHIPPED_KEYWORDS",
    "DIAGNOSIS_KEYWORDS",
    "TASK_STATE_PHRASES",
    "detect_unsupported_shipped_claim",
    "detect_unsupported_diagnosis_claim",
    "detect_unsupported_task_state_claim",
    "scan_orphaned_facts",
    "summarize_scan",
]
