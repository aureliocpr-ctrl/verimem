"""Cycle 2026-05-27 — L1.10 works/confirmed claim detector.

Aurelio mandate 2026-05-27 1h+autonomy: prevent A2 ANTI-HALL violations
("niente FUNZIONA senza pytest/Bash/tool live").

Triangulation: Gemini 2.5 Pro + GPT (via Aurelio Plus Chrome) entrambi
hanno proposto (a) FUNZIONA/WORKS/CONFIRMED come L1.10 prioritary.

Patterns coperti:
- Italian: funziona, confermato, risolto, passa, ok
- English: works, confirmed, passes, succeeded

Evidence accepted: pytest passing tests, bash exit0, smoke-test markers,
file markers, runtime test references.

Closes A2 ANTI-HALL gap (no pytest = no claim verified empirically).
"""
from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

# Italian + English claim keywords (case-insensitive word boundary)
# Note: "ok" / "passa" intentionally limited to specific contexts to avoid FP
_WORKS_PATTERN = re.compile(
    r"\b(?:funziona|funzionante|confermato|confermata|"
    r"works|working|confirmed|"
    r"risolto|risolta|"
    r"passes|passing|succeeded)\b",
    re.IGNORECASE,
)

# "ok" / "passa" require context (preceded by "test/è/è") to avoid FP
_OK_CONTEXTUAL_PATTERN = re.compile(
    r"\b(?:test|tutto|fix|build|ci|deploy|sistema|module|tool|tutto)"
    r"\s+(?:e|è|sembra|risulta|appare)?\s*"
    r"(?:ok|passa)\b",
    re.IGNORECASE,
)

# FP employment (trovato dalla trust console 2026-07-10): "PERSON works
# at/for ORG" è biografia, non un claim di funzionamento — ed è il fatto
# più comune in una memoria personale. Discriminante precision-first: dopo
# "works/working" segue " at|for " + parola Capitalizzata (nome proprio).
# "the system works at scale" resta un claim ('scale' minuscolo); il caso
# "works as a nurse" NON è coperto (FP noto — la rete dietro è L1.20
# semantico, il costo di un miss keyword qui è basso).
_EMPLOYMENT_AFTER_RE = re.compile(r"\s+(?:at|for)\s+[A-Z]")


def _is_employment_use(proposition: str, m: re.Match) -> bool:
    if m.group(0).lower() not in ("works", "working"):
        return False
    return _EMPLOYMENT_AFTER_RE.match(proposition, m.end()) is not None

# Evidence prefixes that count as "runtime/test evidence"
_RUNTIME_EVIDENCE_PREFIXES: tuple[str, ...] = (
    "pytest:", "test:", "bash:", "cmd:", "smoke:",
    "runtime:", "ci:", "smoke_test:",
)

# SCAN-68 audit 2026-06-02 (NONNA): token di ESITO per `test:`, confrontati
# PER-TOKEN (split su non-alfanumerico), NON come substring -> 'compass'/
# 'greenfield'/'bypass' non devono contare come evidenza runtime.
_OUTCOME_TOKENS: frozenset[str] = frozenset(
    {"pass", "passed", "passing", "ok", "green", "exit0"}
)


@dataclass(frozen=True)
class WorksClaimWarning:
    """Warning emitted when a 'works/confirmed' claim lacks runtime proof."""

    matched_text: str
    advice: str


def _has_runtime_evidence(verified_by: Iterable[str] | None) -> bool:
    """Return True iff ``verified_by`` contains at least one runtime
    evidence ref that proves the claim was empirically observed.

    AUDIT 2026-06-02 (NONNA, round 2): i prefissi che implicano un test/comando
    eseguito — ``pytest:`` ``bash:`` ``cmd:`` ``test:`` — richiedono un TOKEN di
    ESITO (pass/passed/passing/ok/green/exit0), confrontato PER-TOKEN (split su
    carattere non-alfanumerico), NON come substring. Cosi 'compass'/'greenfield'/
    'block_okay'/'nonexit0fail' NON contano come esito (chiude il buco substring
    in TUTTI e 4 i branch, non solo in 'test:').
    Accettati col SOLO prefisso (runtime ref): ``smoke:`` ``smoke_test:``
    ``runtime:`` ``ci:``. ``file:`` con ``marker`` nel path.
    """
    if not verified_by:
        return False
    for ref in verified_by:
        if not isinstance(ref, str):
            continue
        lower = ref.lower()
        # pytest:/bash:/cmd:/test: -> serve un TOKEN di esito (NON substring)
        if lower.startswith(("pytest:", "bash:", "cmd:", "test:")) and any(
            tok in _OUTCOME_TOKENS for tok in re.split(r"[^a-z0-9]+", lower)
        ):
            return True
        # smoke / smoke_test / runtime / ci — bare prefix = runtime ref
        if any(lower.startswith(p) for p in
               ("smoke:", "smoke_test:", "runtime:", "ci:")):
            return True
        # file:<path with marker>
        if lower.startswith("file:") and "marker" in lower:
            return True
    return False


def detect_unsupported_works_claim(
    *,
    proposition: str,
    verified_by: Iterable[str] | None,
) -> WorksClaimWarning | None:
    """Return a Warning if proposition contains 'works/confirmed' claim
    AND ``verified_by`` lacks runtime evidence. Else None.

    Args:
        proposition: free-text proposition.
        verified_by: list-of-strings (or None) of evidence refs.

    Returns:
        ``WorksClaimWarning`` with matched text + advice when unsupported;
        ``None`` otherwise.
    """
    if not proposition:
        return None
    # Match main pattern first — skipping employment uses ("works at Acme"),
    # which are biography, not functionality claims
    m = next((cand for cand in _WORKS_PATTERN.finditer(proposition)
              if not _is_employment_use(proposition, cand)), None)
    if m is None:
        # Try contextual ok/passa
        m = _OK_CONTEXTUAL_PATTERN.search(proposition)
        if m is None:
            return None
    matched_text = m.group(0)
    if _has_runtime_evidence(verified_by):
        return None
    return WorksClaimWarning(
        matched_text=matched_text,
        advice=(
            f"Proposition contains works/confirmed claim "
            f"{matched_text!r} but no runtime evidence found in "
            f"verified_by. Add at least one of: "
            f"pytest:<test>_PASS, bash:<cmd>:exit0:<n>, "
            f"cmd:<cmd>:exit0, smoke_test:<id>, "
            f"runtime:<observation>, file:<path>marker."
        ),
    )


__all__ = [
    "WorksClaimWarning",
    "detect_unsupported_works_claim",
]
