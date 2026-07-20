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
    frozenset({"primary", "backup", "secondary", "replica", "standby"}),
    frozenset({"staging", "production"}),
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


# ---------------------------------------------------------------------------
# Lexical expansion (0.7.0): version / sub-year date / negation conflicts.
#
# Same design contract as the numeric detector — deterministic, zero-LLM,
# PRECISION over recall (a false conflict downgrades a true fact, the opposite
# of the trust we sell). Every detector requires the same-subject guard
# (shared distinctive content word) before a difference counts as a conflict.
# Single source of truth for write-time (validate_claim) and batch scanning.
# ---------------------------------------------------------------------------

# Dotted version strings. ≥3 numeric components ("2.3.1") are unambiguous
# anywhere; 2-component ("2.3") only counts near a version keyword, else it
# is a decimal quantity ("2.3 degrees") and belongs to the numeric path.
_VERSION3_RE = re.compile(r"(?<![\w.])v?(\d+(?:\.\d+){2,})(?!\w)(?!\.\d)")
_VERSION2_KW_RE = re.compile(
    r"\b(?:version|versions|release|releases|build|builds|v)[\s:]{0,3}"
    r"(\d+\.\d+(?:\.\d+)*)(?!\w)(?!\.\d)",
    re.IGNORECASE,
)


def extract_versions(text: str) -> set[str]:
    """Version strings in *text*, normalised without the ``v`` prefix."""
    t = text or ""
    out = {m.group(1) for m in _VERSION3_RE.finditer(t)}
    out.update(m.group(1) for m in _VERSION2_KW_RE.finditer(t))
    return out


# The version/date carrier words are not the SUBJECT (like units for the
# numeric path): "version"/"release" shared between two statements says
# nothing about them describing the same thing.
_VERSION_CARRIER_TOKENS = frozenset({"version", "release", "build"})

_CAPS_NAME_RE = re.compile(r"\b[A-Z][a-zA-Z]{2,}\b")


def _named_subjects_disjoint(text_a: str, text_b: str) -> bool:
    """True when BOTH statements name capitalized subjects and the two sets
    are fully disjoint ("Orion ..." vs "Zephyr ...") — different named
    things, so a differing version/date between them is NOT a conflict."""
    ca = set(_CAPS_NAME_RE.findall(text_a or ""))
    cb = set(_CAPS_NAME_RE.findall(text_b or ""))
    return bool(ca) and bool(cb) and not (ca & cb)


def version_conflict(text_a: str, text_b: str) -> tuple[str, str] | None:
    """``(version_a, version_b)`` if the two statements pin DIFFERENT versions
    for the same subject; ``None`` otherwise. Disjoint version sets on a
    shared subject = the value moved (2.3.1 → 4.0.0)."""
    va, vb = extract_versions(text_a), extract_versions(text_b)
    if not va or not vb or (va & vb):
        return None
    shared = (distinctive_tokens(text_a) & distinctive_tokens(text_b))
    if not (shared - _VERSION_CARRIER_TOKENS):
        return None  # unrelated subject (carrier words don't count)
    if _named_subjects_disjoint(text_a, text_b):
        return None  # different named things (Orion vs Zephyr)
    if contrasting_attrs(content_tokens(text_a), content_tokens(text_b)):
        return None
    return (sorted(va)[0], sorted(vb)[0])


# Sub-year dates: ISO ``YYYY-MM-DD`` plus month names (EN). Different YEARS
# are deliberately left to validate_claim's year-disjoint rule — these
# detectors only handle the finer granularity the year rule cannot see.
_ISO_DATE_RE = re.compile(r"\b(1[5-9]\d{2}|20\d{2})-(\d{2})-(\d{2})\b")
_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5,
    "june": 6, "july": 7, "august": 8, "september": 9, "october": 10,
    "november": 11, "december": 12,
}
_MONTH_RE = re.compile(
    r"\b(january|february|march|april|may|june|july|august|september|"
    r"october|november|december)\b(?:\s+(\d{1,2})(?:st|nd|rd|th)?(?!\d))?"
    r"(?:,?\s+(1[5-9]\d{2}|20\d{2}))?",
    re.IGNORECASE,
)


# A BARE month word (no day, no year) is only a date when anchored: the word
# is Capitalized AND preceded by a temporal preposition. Kills the classic
# false positives — "the audit may slip" (modal), "they march to the office"
# (verb) — while keeping "moved to September" / "launches in May".
_TEMPORAL_PREPS = frozenset({
    "in", "on", "by", "until", "till", "before", "after", "since", "during",
    "to", "from", "for", "late", "early", "mid", "next", "last", "this",
    "around", "circa",
})


def extract_dates(text: str) -> set[tuple[int | None, int, int | None]]:
    """``(year, month, day)`` tuples from ISO dates and month names.

    Year/day are ``None`` when the text does not state them ("moved to
    September"). Bare years carry no month → they stay with the year rule.
    A bare month word needs a Capitalized form + temporal preposition (see
    ``_TEMPORAL_PREPS``) — "may"/"march" as modal/verb are not dates.
    """
    t = text or ""
    out: set[tuple[int | None, int, int | None]] = set()
    for m in _ISO_DATE_RE.finditer(t):
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1 <= mo <= 12 and 1 <= d <= 31:
            out.add((y, mo, d))
    for m in _MONTH_RE.finditer(t):
        mo = _MONTHS[m.group(1).lower()]
        day = int(m.group(2)) if m.group(2) else None
        year = int(m.group(3)) if m.group(3) else None
        if day is None and year is None:
            if not m.group(1)[0].isupper():
                continue  # "may slip", "march to the office"
            # Bounded look-behind: only the word IMMEDIATELY before the match
            # decides the anchor, so re-scanning the whole prefix for every
            # match was O(n*m). Measured on 'May ' repeated (audit F8):
            # 20k chars 1.35s, 40k 5.80s, 80k 23.38s — textbook quadratic, and
            # this path runs on every write under validate="full", so one
            # oversized proposition could pin a shared gateway for everyone.
            _win = t[max(0, m.start() - 64):m.start()]
            prev = re.findall(r"[A-Za-z]+", _win)
            if not prev or prev[-1].lower() not in _TEMPORAL_PREPS:
                continue  # Capitalized but unanchored ("May I help")
        out.add((year, mo, day))
    return out


def date_conflict(
    text_a: str, text_b: str,
) -> tuple[tuple[int | None, int, int | None],
           tuple[int | None, int, int | None]] | None:
    """A sub-year date move about the same subject: same (or unstated) year
    but a DIFFERENT month, or same year+month but a different day. Pairs
    with different years return ``None`` (the year-disjoint rule owns them)."""
    da, db = extract_dates(text_a), extract_dates(text_b)
    if not da or not db or (da & db):
        return None
    if not (distinctive_tokens(text_a) & distinctive_tokens(text_b)):
        return None  # unrelated subject
    if _named_subjects_disjoint(text_a, text_b):
        return None  # different named things
    if contrasting_attrs(content_tokens(text_a), content_tokens(text_b)):
        return None
    for (ya, ma, dda) in da:
        for (yb, mb, ddb) in db:
            same_year = ya is None or yb is None or ya == yb
            if not same_year:
                continue  # year rule's jurisdiction
            if ma != mb:
                return ((ya, ma, dda), (yb, mb, ddb))
            if dda is not None and ddb is not None and dda != ddb:
                return ((ya, ma, dda), (yb, mb, ddb))
    return None


# Polarity flip: the same statement with a negator on exactly one side.
_NEGATOR_RE = re.compile(
    r"\b(?:not|never|no longer|cannot|can't|won't|isn't|aren't|wasn't|"
    r"weren't|doesn't|don't|didn't|nor)\b",
    re.IGNORECASE,
)


def _has_negator(text: str) -> bool:
    return bool(_NEGATOR_RE.search(text or ""))


def _negated_tokens(text: str) -> set[str]:
    """Content words in the negator's SCOPE: the first 1-2 alpha tokens right
    after each negator, singularised like :func:`content_tokens`."""
    t = text or ""
    out: set[str] = set()
    for m in _NEGATOR_RE.finditer(t):
        following = re.findall(r"[a-zA-Z]{4,}", t[m.end():])[:2]
        for w in following:
            w = w.lower()
            if w.endswith("ies"):
                w = w[:-3] + "y"
            elif w.endswith("s") and len(w) > 3:
                w = w[:-1]
            out.add(w)
    return out


def negation_conflict(text_a: str, text_b: str) -> str | None:
    """The shared predicate token when *text_a*/*text_b* state the SAME thing
    with OPPOSITE polarity ("is signed" vs "is not signed"); else ``None``.

    Precision guards: the polarity must differ, the content-token sets must
    be near-identical (Jaccard ≥ 0.6 with ≥2 shared tokens), AND the word in
    the negator's scope must itself be SHARED — "complete, not blocked" does
    not flip "complete" (the negator scopes "blocked", absent from the other
    statement)."""
    na, nb = _has_negator(text_a), _has_negator(text_b)
    if na == nb:
        return None  # same polarity → no flip
    ca, cb = content_tokens(text_a), content_tokens(text_b)
    shared = ca & cb
    union = ca | cb
    if len(shared) < 2 or not union or (len(shared) / len(union)) < 0.6:
        return None  # different statement, not a flip of this one
    if contrasting_attrs(ca, cb):
        return None
    scoped = _negated_tokens(text_a if na else text_b)
    scoped_shared = scoped & shared
    if scoped and not scoped_shared:
        return None  # the negation targets a word the other side never states
    if scoped_shared:
        return sorted(scoped_shared)[0]
    return sorted(shared)[0]


def lexical_conflict(text_a: str, text_b: str) -> tuple[str, str] | None:
    """First lexical conflict between two statements as ``(kind, detail)`` —
    kind ∈ {"numeric", "version", "date", "negation"} — or ``None``.

    The one-call façade over the four deterministic detectors, so callers
    (gate, scanners, benches) share identical semantics."""
    q = numeric_conflict(text_a, text_b)
    if q is not None:
        u, va, vb = q
        return ("numeric", f"{va:g} {u} vs {vb:g} {u}")
    v = version_conflict(text_a, text_b)
    if v is not None:
        return ("version", f"{v[0]} vs {v[1]}")
    d = date_conflict(text_a, text_b)
    if d is not None:
        return ("date", f"{d[0]} vs {d[1]}")
    n = negation_conflict(text_a, text_b)
    if n is not None:
        return ("negation", f"polarity flip on '{n}'")
    return None


# Ordinal EVENT indices ("day 4", "sprint 3", "week 12"): a cardinal counter of
# repeated events, NOT a calendar value. Two statements carrying DIFFERENT
# indices of the same kind narrate two distinct events (a diary), so neither
# supersedes nor contradicts the other. Calendar dates (March, 2025-03-06) are
# deliberately excluded — "launches in March" -> "launches in September" is one
# VALUE moving, which the evolution path must keep superseding.
_EVENT_INDEX_RE = re.compile(
    r"\b(day|night|week|month|quarter|sprint|round|session|meeting|"
    r"iteration|cycle|episode|phase|step|attempt|run|note|entry|item|log|chapter|part|lesson|task)\s+(\d{1,4})\b",
    re.IGNORECASE,
)


def event_indices(text: str) -> set[tuple[str, int]]:
    """``(kind, n)`` ordinal event indices in *text* ("day 4" -> ("day", 4))."""
    return {(m.group(1).lower(), int(m.group(2)))
            for m in _EVENT_INDEX_RE.finditer(text or "")}


def distinct_event_indices(text_a: str, text_b: str) -> bool:
    """True when the two statements index DIFFERENT events of the same kind
    ("On day 4 ..." vs "On day 5 ..."): distinct diary entries, not an
    evolution and not a contradiction. False when either carries no event
    index, or the shared kind has the same index."""
    ea, eb = event_indices(text_a), event_indices(text_b)
    if not ea or not eb:
        return False
    kinds_a = {k for (k, _n) in ea}
    kinds_b = {k for (k, _n) in eb}
    for k in kinds_a & kinds_b:
        na = {n for (kk, n) in ea if kk == k}
        nb = {n for (kk, n) in eb if kk == k}
        if na and nb and not (na & nb):
            return True  # same kind, disjoint indices -> different events
    return False


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
    "extract_versions",
    "version_conflict",
    "extract_dates",
    "date_conflict",
    "negation_conflict",
    "lexical_conflict",
    "event_indices",
    "distinct_event_indices",
]
