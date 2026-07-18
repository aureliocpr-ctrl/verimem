"""Shared numeric-quantity contradiction primitives.

A *numeric conflict* between two statements = they describe the SAME
subject (share a distinctive, non-unit content word) and assert a
DIFFERENT value for the SAME normalised unit, with NO contrasting
qualifier ("read" vs "write"). Pure lexical, zero LLM, embedding-free.

Single source of truth used by BOTH:
  • the write-time gate (``validate_claim`` — sibling of its year-disjoint
    contradiction rule), and
  • the batch corpus scanner (``facts_conflict.find_numeric_conflicts`` —
    surfaces numeric inconsistencies already present in memory).

Keeping the two paths on identical semantics is the point: a confab that
the write gate would flag must also be findable retroactively in the
corpus, and vice-versa.
"""
from __future__ import annotations

import re

# 4-digit years (1500–2099). Bare years are NOT quantities — they belong
# to the year-disjoint rule in validate_claim, so the two detectors never
# double-handle the same number.
YEAR_RE = re.compile(r"\b(?:1[5-9]\d{2}|20\d{2})\b")

# A STANDALONE number optionally followed by a unit word: "30 minutes",
# "200ms", "1024 entries", "7-snapshot". The leading ``(?<![\w.])`` and
# trailing ``(?![\w])`` anchors keep digits EMBEDDED in identifiers OUT —
# commit SHAs ("a64d252"), versions ("v38"), loop ids ("loop178") are NOT
# quantities. (Empirically critical: without the anchors a live-corpus scan
# produced ~700k false conflicts from SHA/id digits.)
# SECURITY (opus CodeQL triage 2026-07-18, alert [26]): the unit group had two
# adjacent unbounded ``\s*`` around an optional ``-?`` → quadratic backtracking
# on a number followed by a long run of spaces with no trailing letter. It runs
# on ``fact.proposition`` (documented up to 64KB, NOT capped by the L1 gate), so
# a tenant writing "5"+" "*60000 stalled the server ~30s per fact. Bounding the
# whitespace to 3 removes the ReDoS while still matching every real form
# ("5kg", "5 kg", "5-kg", "5 - kg") — real quantities never have >3 spaces.
_QUANT_RE = re.compile(
    r"(?<![\w.])(\d+(?:\.\d+)?)(?:\s{0,3}-?\s{0,3}([A-Za-z]+))?(?![\w])"
)

# Function words that can FOLLOW a number but are never units ("30 and 45",
# "5 of 10"). Stripped to a bare (unitless) number, which the conflict check
# then ignores.
_NON_UNIT_WORDS = frozenset({
    "and", "or", "to", "of", "in", "on", "at", "by", "for", "the", "an",
    "is", "are", "was", "were", "be", "per", "via", "with", "from", "but",
    "as", "that", "than", "then", "plus", "over", "into", "out", "more",
    "e", "o", "di", "da", "su", "con", "tra", "fra", "ed", "il", "la", "un",
})

# Unit synonyms → canonical form so "200ms" and "500 milliseconds" compare
# and "30 minutes"/"45 minutes" share unit "min". Plural/`-ies` handled
# generically in :func:`norm_unit`.
_UNIT_SYN = {
    "ms": "ms", "msec": "ms", "msecs": "ms",
    "millisecond": "ms", "milliseconds": "ms",
    "s": "s", "sec": "s", "secs": "s", "second": "s", "seconds": "s",
    "m": "min", "min": "min", "mins": "min", "minute": "min", "minutes": "min",
    "h": "h", "hr": "h", "hrs": "h", "hour": "h", "hours": "h",
    "d": "day", "day": "day", "days": "day",
}

# ≥4-char filler words excluded from the distinctive-overlap check.
_CONTENT_STOP = frozenset({
    "with", "from", "into", "over", "each", "after", "before", "than",
    "that", "this", "these", "those", "their", "your", "default", "about",
    "while", "when", "then", "also", "only", "most", "more", "less",
    "such", "some", "any", "via", "per", "upto", "starting", "uses",
    "used", "using", "have", "has", "was", "were", "are", "the",
})

# Contrasting qualifiers: if two statements each hold a DIFFERENT member of
# one group they describe DIFFERENT attributes ("read timeout" vs "write
# timeout") — a same-unit/different-value pair is then NOT a contradiction.
# Conservative and not exhaustive, but kills the common false-positive
# class. Tokens are singularised upstream by :func:`content_tokens`.
CONTRAST_QUALIFIERS: tuple[frozenset[str], ...] = (
    frozenset({"read", "write"}),
    frozenset({"request", "response"}),
    frozenset({"upload", "download"}),
    frozenset({"input", "output"}),
    frozenset({"send", "receive"}),
    frozenset({"inbound", "outbound"}),
    frozenset({"ingress", "egress"}),
    frozenset({"source", "destination"}),
    frozenset({"encode", "decode"}),
    frozenset({"encrypt", "decrypt"}),
    frozenset({"push", "pull"}),
    frozenset({"client", "server"}),
    frozenset({"minimum", "maximum"}),
)


def norm_unit(word: str) -> str:
    """Canonicalise a unit word (synonyms + plural/`-ies` singularisation)."""
    w = (word or "").lower()
    if w in _UNIT_SYN:
        return _UNIT_SYN[w]
    if len(w) > 3 and w.endswith("ies"):
        return w[:-3] + "y"
    if len(w) > 3 and w.endswith("s"):
        return w[:-1]
    return w


def extract_quantities(text: str) -> set[tuple[str, float]]:
    """Extract ``(unit_norm, value)`` pairs from text; bare YEARS excluded."""
    out: set[tuple[str, float]] = set()
    for m in _QUANT_RE.finditer(text or ""):
        num_s, unit_s = m.group(1), (m.group(2) or "")
        if unit_s.lower() in _NON_UNIT_WORDS:
            unit_s = ""  # a following function word is not a unit
        if not unit_s and YEAR_RE.fullmatch(num_s):
            continue  # bare year → year path, not a quantity
        try:
            val = float(num_s)
        except ValueError:  # pragma: no cover — regex guarantees numeric
            continue
        out.add((norm_unit(unit_s), val))
    return out


def content_tokens(text: str) -> set[str]:
    """Lower-cased alpha tokens ≥4 chars minus fillers, lightly singularised.

    Used as the topical-overlap precision guard: two statements must share
    a *distinctive* (non-unit) content word before a same-unit/different-
    value pair counts as a contradiction.
    """
    toks = re.findall(r"[a-zA-Z]{4,}", (text or "").lower())
    out: set[str] = set()
    for t in toks:
        if t in _CONTENT_STOP:
            continue
        if t.endswith("ies"):
            t = t[:-3] + "y"
        elif t.endswith("s") and len(t) > 3:
            t = t[:-1]
        out.add(t)
    return out


def contrasting_attrs(a_tokens: set[str], b_tokens: set[str]) -> bool:
    """True if the two token sets describe DIFFERENT attributes — each holds
    a different member of a contrasting-qualifier group (read vs write)."""
    for grp in CONTRAST_QUALIFIERS:
        ca, cb = a_tokens & grp, b_tokens & grp
        if ca and cb and ca != cb:
            return True
    return False


def distinctive_tokens(text: str) -> set[str]:
    """Content tokens minus the statement's own unit words (the 'subject')."""
    units = {u for (u, _v) in extract_quantities(text) if u}
    return {t for t in content_tokens(text) if norm_unit(t) not in units}


def conflict_from_parts(
    qa: set[tuple[str, float]], ca: set[str],
    qb: set[tuple[str, float]], cb: set[str],
) -> tuple[str, float, float] | None:
    """Core numeric-conflict check on PRE-COMPUTED quantities/content tokens.

    Lets a batch scan precompute ``(quantities, content_tokens)`` once per
    fact and reuse them across the O(n²) pair loop without re-parsing.
    Guards identical to :func:`numeric_conflict`.
    """
    if not qa or not qb:
        return None
    units_a = {u for (u, _v) in qa if u}
    units_b = {u for (u, _v) in qb if u}
    da = {t for t in ca if norm_unit(t) not in units_a}
    db = {t for t in cb if norm_unit(t) not in units_b}
    if not (da & db):
        return None  # unrelated subject
    if contrasting_attrs(ca, cb):
        return None  # different attribute
    for (ua, va) in qa:
        if not ua:
            continue  # bare unitless number → too ambiguous
        for (ub, vb) in qb:
            if ua == ub and va != vb:
                return (ua, va, vb)
    return None


def agreement_from_parts(
    qa: set[tuple[str, float]], ca: set[str],
    qb: set[tuple[str, float]], cb: set[str],
) -> tuple[str, float] | None:
    """Twin of :func:`conflict_from_parts` — returns ``(unit, value)`` when a
    and b assert the SAME value for the same unit about the same subject
    (no contrasting qualifier); else ``None``. The positive signal behind
    corroboration: two statements that AGREE on a specific quantity.
    """
    if not qa or not qb:
        return None
    units_a = {u for (u, _v) in qa if u}
    units_b = {u for (u, _v) in qb if u}
    da = {t for t in ca if norm_unit(t) not in units_a}
    db = {t for t in cb if norm_unit(t) not in units_b}
    if not (da & db):
        return None
    if contrasting_attrs(ca, cb):
        return None
    for (ua, va) in qa:
        if not ua:
            continue
        for (ub, vb) in qb:
            if ua == ub and va == vb:
                return (ua, va)
    return None


def numeric_conflict(
    text_a: str, text_b: str,
) -> tuple[str, float, float] | None:
    """Return ``(unit, value_a, value_b)`` if *text_a* and *text_b* state a
    DIFFERENT value for the same unit about the same subject; else ``None``.

    Guards (precision over recall — a false conflict downgrades a true
    fact, the opposite of the trust we sell):
      • both must carry a quantity;
      • they must share ≥1 distinctive (non-unit) content word (same
        subject) — stops coincidental same-unit matches across topics;
      • no contrasting qualifier (read/write, client/server, …);
      • same normalised unit, different value.
    """
    return conflict_from_parts(
        extract_quantities(text_a), content_tokens(text_a),
        extract_quantities(text_b), content_tokens(text_b),
    )


__all__ = [
    "YEAR_RE",
    "CONTRAST_QUALIFIERS",
    "norm_unit",
    "extract_quantities",
    "content_tokens",
    "contrasting_attrs",
    "distinctive_tokens",
    "conflict_from_parts",
    "numeric_conflict",
]
