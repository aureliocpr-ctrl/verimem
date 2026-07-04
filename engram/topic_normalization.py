"""Cycle 214 (2026-05-23) — topic normalisation primitive.

Closes the empirical finding from cycle 213: topic naming in the
real corpus is inconsistent (``cycle/175`` vs
``project/hippoagent/cycle175`` vs ``cycles/175.1`` etc.) → emergent
skill detection sees disparate communities.

This module ships a pure normalisation function + a similarity
metric so callers can cluster facts by topic *family* rather than
exact string.

Algorithm
---------
``normalize_topic(t)`` →

  1. Lowercase + strip.
  2. Collapse whitespace runs to single ``-``.
  3. Replace common separators (``_``, ``::``, ``-``) with ``/``.
  4. Drop short numeric-only segments (``"175"`` after ``"cycle"``).
  5. Drop common scope prefixes (``project/``, ``cycles/``, ``cycle/``).
  6. Drop trailing date stamps (``-2026-05-23``).

The result is a canonical "topic family key" — e.g.
``cycle/175`` and ``project/hippoagent/cycle175.1`` both normalise
to ``hippoagent`` (the most informative remaining segment).

``topic_similarity(a, b)`` → float in [0, 1] —
  Jaccard over the normalised segment set.

Defensive: None / empty → "".
"""
from __future__ import annotations

import re

_DROP_SCOPES = {
    "project", "cycles", "cycle", "lessons", "decisions",
    "research", "lab", "dialog", "preferences", "archive",
}

#: Trailing date pattern: ``-2026-05-23`` etc.
_DATE_SUFFIX_RE = re.compile(r"-?\d{4}-\d{2}-\d{2}$")

#: Pure-numeric segment (could be a cycle id like ``175``).
_NUMERIC_SEG_RE = re.compile(r"^\d+(\.\d+)?$")


def normalize_topic(raw: str | None) -> str:
    """Canonicalise a topic string to its 'family key' form."""
    if not raw:
        return ""
    s = str(raw).strip().lower()
    if not s:
        return ""
    # Drop trailing date stamps.
    s = _DATE_SUFFIX_RE.sub("", s)
    # Replace separators uniformly with '/'.
    s = s.replace("::", "/").replace("_", "/").replace("\\", "/")
    # Collapse runs of '/'.
    s = re.sub(r"/+", "/", s).strip("/")
    if not s:
        return ""
    segments = [seg for seg in s.split("/") if seg]
    # Drop pure-numeric segments + drop scope prefixes when there's
    # at least one other segment to keep.
    filtered: list[str] = []
    for seg in segments:
        if _NUMERIC_SEG_RE.match(seg):
            continue
        if seg in _DROP_SCOPES and len(segments) > 1:
            continue
        # Strip trailing cycle-id digits (e.g. 'cycle175.1' → 'cycle').
        seg_clean = re.sub(r"\d+(\.\d+)?$", "", seg).strip("-")
        # Cycle 215.1: real-corpus topics often look like
        # 'master-fact-v5-clp-v0.4.0-phase2-r0-replay'. Take only the
        # first 2 hyphen-tokens of a long segment so it collapses to
        # 'master-fact'. This is the empirical fix for the cycle-213
        # 'topics too unique' finding.
        if seg_clean.count("-") >= 2:
            parts = [p for p in seg_clean.split("-") if p]
            seg_clean = "-".join(parts[:2])
        if seg_clean:
            filtered.append(seg_clean)
    # Keep only the first 2 segments — beyond that is usually
    # fact-specific noise (cycle 215.1 empirical).
    filtered = filtered[:2]
    return "/".join(filtered)


def topic_similarity(a: str | None, b: str | None) -> float:
    """Jaccard similarity over normalised topic segments. ``∈ [0, 1]``."""
    na = normalize_topic(a)
    nb = normalize_topic(b)
    if not na and not nb:
        return 1.0
    if not na or not nb:
        return 0.0
    sa = {s for s in na.split("/") if s}
    sb = {s for s in nb.split("/") if s}
    if not sa or not sb:
        return 0.0
    inter = sa & sb
    union = sa | sb
    return len(inter) / len(union)


def group_by_topic_family(
    topics: list[str],
    *,
    threshold: float = 0.5,
) -> dict[str, list[str]]:
    """Bucket raw topic strings by similarity to the first member.

    Greedy single-pass: each topic joins the existing family with
    similarity ≥ threshold, otherwise starts a new family. Family
    keys are the normalised representative.
    """
    families: dict[str, list[str]] = {}
    for raw in topics:
        if not raw:
            continue
        norm = normalize_topic(raw)
        if not norm:
            continue
        # Find an existing family.
        matched = None
        for key in families:
            if topic_similarity(norm, key) >= float(threshold):
                matched = key
                break
        if matched is None:
            families[norm] = [raw]
        else:
            families[matched].append(raw)
    return families


__all__ = [
    "normalize_topic",
    "topic_similarity",
    "group_by_topic_family",
]
