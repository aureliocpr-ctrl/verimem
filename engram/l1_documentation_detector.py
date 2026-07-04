"""Cycle 2026-05-27 (round 6) — L1.14 documentation claim detector.

Claude architectural choice round 6: (g) documented/explained come
ortogonal a tutti detector esistenti. Closes gap "ho documentato" senza
file marker docs.

Patterns coperti:
- English: documented, well-documented, explained, described
- Italian: documentato, spiegato, descritto

Evidence accepted (docs proof):
- docs:<path> or md:<file>
- file:<path>.md or file:<path>/README
- readme:<id>
- changelog:<entry>_added
- comment:<file>:<line>_added
"""
from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

_DOC_PATTERN = re.compile(
    r"\b(?:documented|well[- ]documented|"
    r"explained|described|"
    r"documentato|documentata|spiegato|spiegata|"
    r"descritto|descritta)\b",
    re.IGNORECASE,
)

_DOC_EVIDENCE_PREFIXES: tuple[str, ...] = (
    "docs:", "md:", "readme:", "readme.md:",
    "changelog:", "comment:",
)


@dataclass(frozen=True)
class DocClaimWarning:
    matched_text: str
    advice: str


def _has_doc_evidence(verified_by: Iterable[str] | None) -> bool:
    if not verified_by:
        return False
    for ref in verified_by:
        if not isinstance(ref, str):
            continue
        lower = ref.lower()
        if any(lower.startswith(p) for p in _DOC_EVIDENCE_PREFIXES):
            return True
        # file:<path>.md or file:<path>/README*
        if lower.startswith("file:") and (
            ".md" in lower or "readme" in lower or "/docs/" in lower
        ):
            return True
    return False


def detect_unsupported_doc_claim(
    *,
    proposition: str,
    verified_by: Iterable[str] | None,
) -> DocClaimWarning | None:
    if not proposition:
        return None
    m = _DOC_PATTERN.search(proposition)
    if m is None:
        return None
    matched_text = m.group(0)
    if _has_doc_evidence(verified_by):
        return None
    return DocClaimWarning(
        matched_text=matched_text,
        advice=(
            f"Proposition contains documentation claim {matched_text!r} "
            f"but no docs evidence in verified_by. Add at least one of: "
            f"docs:<path>, md:<file>, file:<path>.md, readme:<id>, "
            f"changelog:<entry>_added, comment:<file>:<line>."
        ),
    )


__all__ = ["DocClaimWarning", "detect_unsupported_doc_claim"]
