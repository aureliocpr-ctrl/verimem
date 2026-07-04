"""Cycle #75 - L1-SYNTAX pollution detection for semantic-memory facts.

Detects fact propositions that contain malformed XML/tool-call markup
leaked from the host parser (e.g. nested ``<parameter name=...>`` or
``</proposition>`` literal tokens inside the proposition body).

Empirical baseline (2026-05-15 audit on Aurelio corpus):
  - 110/798 facts (13.8%) carry XML pollution
  - 88/798 facts (11.0%) have NULL/empty topic

Bug origin: when the MCP host emits a malformed tool-call envelope,
the server-side parser sometimes silently extracts only the
``proposition`` field and stuffs the rest of the XML payload into
its body. Result: facts persisted with `topic=''` and propositions
that end in literal ``</proposition>\\n<parameter name="topic">...``
text. The pollution corrupts retrieval (proposition text is noisy)
and aggregation (topic is missing).

This module is the *detection + gate* layer:

  - `detect_xml_markup(text)` -> list of marker names found
  - `is_polluted(text)` -> bool
  - `validate_proposition(text)` -> raises `PollutionError` if dirty
  - `sanitize_proposition(text)` -> best-effort recovery
  - `scan_facts(facts)` -> bulk audit returning polluted records

The validate gate is intended to be wired into `hippo_remember` so
new writes are rejected before persistence. The scan + sanitize
functions handle the cleanup of the already-polluted backlog.

Honest limits:
  - Detection is regex-only (no proper XML parser): we look for the
    literal markers that real-world pollution actually carries.
  - Sanitize is best-effort: it strips the first XML marker and
    everything after it. Useful when the leading text is meaningful;
    not magic.
  - We do NOT flag bare ``<`` or ``>`` to avoid false positives on
    "x < y" maths or "->" arrows.
"""
from __future__ import annotations

import re
from typing import Any


class PollutionError(ValueError):
    """Raised when a proposition fails syntax validation."""


# Patterns are anchored to literal markup tokens we have actually
# observed in polluted facts. Each entry: (marker_name, compiled_regex).
_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    # Parameter tag — nested tool-call payload
    ("parameter_tag", re.compile(r"<\s*parameter\b[^>]*>", re.IGNORECASE)),
    # Proposition close tag — host echoed its own envelope
    ("proposition_close", re.compile(r"<\s*/\s*proposition\s*>", re.IGNORECASE)),
    # Proposition open tag — same, opening form
    ("proposition_open", re.compile(r"<\s*proposition\b[^>]*>", re.IGNORECASE)),
    # Invoke opening tag — tool call envelope literal
    ("invoke_tag", re.compile(r"<\s*invoke\b[^>]*>", re.IGNORECASE)),
    # Invoke closing tag — envelope tail (cycle #75 adversarial fix:
    # sanitize cuts on \n</invoke> so detect MUST recognize it too,
    # otherwise the gate-via-detect and gate-via-sanitize paths
    # disagree on the same input).
    ("invoke_close", re.compile(r"<\s*/\s*invoke\s*>", re.IGNORECASE)),
    # Parameter closing tag — same coherence rationale
    ("parameter_close", re.compile(r"<\s*/\s*parameter\s*>", re.IGNORECASE)),
    # antml-prefixed parameter (host-specific)
    ("antml_tag", re.compile(r"<\s*antml\s*:", re.IGNORECASE)),
    # function_calls envelope (Claude tool format)
    ("function_calls", re.compile(r"<\s*function_calls\b", re.IGNORECASE)),
]

# Safe-cut anchors. We cut ONLY when the markup looks like an actual
# tool-call envelope leak, not when it's descriptive backtick code.
# Three signatures qualify:
#
#   1. ``</proposition>``                — server echoed its own
#                                          closing envelope tag
#   2. ``\n</invoke>`` / ``\n</parameter>``  — newline-anchored
#                                          closing tag (envelope is
#                                          always written on its own
#                                          line; backtick code is
#                                          always inline)
#   3. ``\n<parameter name=``            — newline-anchored opening
#                                          of a sibling parameter
#
# Empirical rationale (2026-05-15 audit on Aurelio corpus, 798 facts):
#   - 110/111 polluted facts carry ``</proposition>`` as anchor
#   - 1/111 has only inline ``<invoke>`` inside backticks (legit
#     descriptive text — must be PRESERVED)
#   - The cycle-#70 tests further document the newline-anchored
#     envelope pattern (\n</invoke>\n<parameter name=...).
_SAFE_CUT_RE = re.compile(
    r"<\s*/\s*proposition\s*>"
    r"|\n\s*<\s*/\s*invoke\s*>"
    r"|\n\s*<\s*/\s*parameter\s*>"
    r"|\n\s*<\s*parameter\b[^>]*>",
    re.IGNORECASE,
)


def detect_xml_markup(text: str | None) -> list[str]:
    """Return list of marker names found in ``text``.

    Empty/None input -> empty list. The returned list preserves
    pattern order (parameter_tag, proposition_close, ...).
    """
    if not text:
        return []
    found: list[str] = []
    for name, pat in _PATTERNS:
        if pat.search(text):
            found.append(name)
    return found


def is_polluted(text: str | None) -> bool:
    """True if ``text`` contains any known XML pollution marker."""
    return bool(detect_xml_markup(text))


def validate_proposition(text: str | None) -> None:
    """Raise ``PollutionError`` if ``text`` is empty or polluted.

    Wired as a gate inside ``hippo_remember`` to refuse persistence of
    facts whose proposition body is malformed. Clean text returns
    None silently.
    """
    if text is None or not text.strip():
        raise PollutionError("empty_proposition")
    markers = detect_xml_markup(text)
    if markers:
        raise PollutionError(f"xml_pollution: {markers}")


def sanitize_proposition(text: str | None) -> str:
    """Best-effort recovery: strip the envelope-pollution payload.

    Cuts at the FIRST ``</proposition>`` occurrence and drops
    everything from there to end-of-string. Trailing whitespace is
    trimmed. Returns the input as-is when no envelope anchor is
    found — content that mentions ``<parameter>`` or ``<invoke>``
    inside backticks (legitimate descriptive text about the bug
    itself) is preserved.

    Empirical rationale (2026-05-15 audit on Aurelio corpus): 110/111
    polluted facts carry ``</proposition>`` as anchor; the only
    outlier is a fact that legitimately describes XML markup inside
    a code span and should NOT be truncated.
    """
    if not text:
        return ""
    m = _SAFE_CUT_RE.search(text)
    if not m:
        return text
    return text[: m.start()].rstrip(" \t\r\n>")


def scan_facts(facts: list[Any]) -> dict[str, Any]:
    """Bulk audit. Returns a structured report.

    Each fact must duck-type with ``id`` and ``proposition`` attrs.

    Returns: ``{n_total, n_polluted, polluted: [{id, topic, markers,
    sample}]}`` where ``sample`` is the first 160 chars of the
    polluted proposition for visual inspection.
    """
    polluted: list[dict[str, Any]] = []
    n_total = 0
    for f in facts:
        n_total += 1
        prop = getattr(f, "proposition", "") or ""
        markers = detect_xml_markup(prop)
        if not markers:
            continue
        polluted.append({
            "id": getattr(f, "id", ""),
            "topic": getattr(f, "topic", "") or "",
            "markers": markers,
            "sample": prop[:160],
        })
    return {
        "n_total": n_total,
        "n_polluted": len(polluted),
        "polluted": polluted,
    }


__all__ = [
    "PollutionError",
    "detect_xml_markup",
    "is_polluted",
    "validate_proposition",
    "sanitize_proposition",
    "scan_facts",
]
