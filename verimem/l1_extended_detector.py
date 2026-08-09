"""Cycle 183 (2026-05-23) — L1 extended detector: bug-fix keyword family.

Extends the cycle-128 SHIPPED-family L1 anti-confab gate with a parallel
detector for bug-fix claims ("FIXED the race condition", "RESOLVED the
deadlock", ...) that lack an evidence ref.

Design
------
Composable side-by-side module — does NOT touch
``engram/anti_confab_gate.py``. The new detector returns a
``FixClaimWarning`` instance with the same fields any future
gate-orchestrator cycle can splice into the existing warnings list:

  * ``keyword``: which keyword matched (string)
  * ``advice``: human-readable suggestion

Decision rule (mirrors cycle-128 family)
----------------------------------------
A fact's proposition is flagged when:

  * the proposition contains a FIX_KEYWORDS entry as a WHOLE WORD
    (non piu' come substring: ``unresolved`` e' il contrario di
    ``resolved`` — vedi il commento su ``_FIX_WORD_RE``)
  * ``verified_by`` has NO entry that proves the fix actually landed,
    where "proves" means at least one of:
      - starts with ``commit:`` / ``pr:`` / ``file:`` / ``git:``
      - starts with ``pytest:`` and ends with ``_PASS`` (test green)
      - starts with ``bash:`` and contains ``exit0`` (process succeed)

Empirical motivation
--------------------
The cycle-128 SHIPPED family caught 2/7 of the 2026-05-17 self-
confabulations. The remaining 5 had shapes like "FIXED the recall bug"
or "RESOLVED the contradiction" with no ``pytest:`` ref. This cycle
closes that subset.

Closes gap §5 #3 of ``docs/sota/L0-L3-anti-confab-layers.md`` (cycle 180).
"""
from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

#: Canonical bug-fix verbs, in upper case perche' il confronto e'
#: case-insensitive e la warning riporta la forma canonica.
FIX_KEYWORDS = frozenset({"FIXED", "RESOLVED", "PATCHED", "REPAIRED"})

#: Le stesse parole, ma confrontate come PAROLE INTERE.
#:
#: PERCHE' (2026-08-04, dal corpus di produzione): la scansione era un
#: ``.upper()`` + substring, e ``UNRESOLVED`` contiene ``RESOLVED``. Due dei
#: dodici fatti ripristinati a mano erano quarantinati per questo:
#:
#:   «…riporta due blocchi DISPUTED unresolved con lo stesso record in
#:     conflitto»  ->  L1.8: FIX-family claim 'RESOLVED' lacks an evidence ref
#:
#: Il fatto dice che due conflitti NON sono risolti, e il detector lo legge
#: come la dichiarazione di averli risolti. E' il caso peggiore per un gate
#: anti-confabulazione: non blocca una millanteria, blocca la sua SMENTITA —
#: chi scrive «il problema non e' risolto» si vede chiedere la prova di
#: averlo risolto. Stesso effetto su ``resolved_at``, che e' il nome di una
#: colonna.
#:
#: LA CURA C'ERA GIA' NEL REPO, sul lato delle PROVE: il fratello
#: ``l1_tested_detector._has_tested_evidence`` confronta per token e non per
#: substring, e il commento accanto spiega perche' (``test:greenfield`` non
#: deve contare). La stessa precauzione non era mai stata portata sul lato
#: della PROPOSIZIONE — la classe «la cura c'era e mancava lo sweep».
_FIX_WORD_RE = re.compile(
    r"\b(?:" + "|".join(sorted(FIX_KEYWORDS)) + r")\b",
    re.IGNORECASE,
)

#: Verified-by prefixes that count as "git-state evidence".
_COMMIT_REF_PREFIXES = ("commit:", "pr:", "file:", "git:")


@dataclass(frozen=True)
class FixClaimWarning:
    """Warning emitted when a FIX-family claim lacks evidence.

    Mirrors the shape used by the cycle-128 detectors so a future
    gate-orchestrator cycle can append instances of this class into
    the existing warnings list without case-splitting on type.
    """

    keyword: str
    advice: str


def _has_evidence_ref(verified_by: Iterable[str] | None) -> bool:
    """Return True iff ``verified_by`` contains at least one accepted
    evidence ref.

    Accepted shapes (case-insensitive on the prefix):
      * ``commit:`` / ``pr:`` / ``file:`` / ``git:``     — git-state
      * ``pytest:<...>_PASS``                            — test pass
      * ``bash:<...>exit0<...>``                         — process OK
    """
    if not verified_by:
        return False
    for ref in verified_by:
        if not isinstance(ref, str):
            continue
        lower = ref.lower()
        if any(lower.startswith(p) for p in _COMMIT_REF_PREFIXES):
            return True
        if lower.startswith("pytest:") and lower.endswith("_pass"):
            return True
        if lower.startswith("bash:") and "exit0" in lower:
            return True
    return False


def detect_unsupported_fix_claim(
    *,
    proposition: str,
    verified_by: Iterable[str] | None,
) -> FixClaimWarning | None:
    """Return a Warning if the proposition contains a FIX_KEYWORDS entry
    AND ``verified_by`` lacks any accepted evidence ref. Else None.

    Args:
        proposition: free-text proposition of the fact about to be
            persisted.
        verified_by: list-of-strings (or None) of evidence refs.

    Returns:
        ``FixClaimWarning`` with the triggering keyword + a
        human-readable advice when the claim is unsupported; ``None``
        otherwise.
    """
    if not proposition:
        return None
    m = _FIX_WORD_RE.search(proposition)
    if m is None:
        return None
    hit_keyword = m.group(0).upper()
    if _has_evidence_ref(verified_by):
        return None
    return FixClaimWarning(
        keyword=hit_keyword,
        advice=(
            f"Proposition contains bug-fix keyword {hit_keyword!r} but "
            "no evidence ref found in verified_by. Add at least one of: "
            "commit:<sha>, pr:#NNN, file:<path>:<line>, "
            "pytest:<test_id>_PASS, or bash:<cmd>:exit0:<n>."
        ),
    )


__all__ = [
    "FIX_KEYWORDS",
    "FixClaimWarning",
    "detect_unsupported_fix_claim",
]
