"""Cycle #110.D (2026-05-16) — Legacy corpus audit.

Aurelio audit 2026-05-16: "815/864 fact sono ``legacy_unverified``,
nascosti dal filter cycle 109 ma il pollution è solo spostato sotto
il tappeto. Cycle 110.D classifica i 815 in 3 bucket per decisione
umana."

Classifier
----------
Pure decision function ``classify_legacy_fact(Fact, *, now)`` that
inspects the proposition + confidence + age and returns one of:

* ``verified_on_rereading``: proposition contains tool-call / source
  references that look like provenance evidence even though the fact
  was migrated as ``legacy_unverified``. Recommendation: PROMOTE to
  status=verified. Signals: ``bash:``, ``file:<path>:<line>``,
  ``url:`` / ``arxiv.org/`` / ``github.com/``, ``sha256:``,
  ``pytest:`` / ``pytest_collect``, ``exit0``.

* ``forgettable``: proposition is short / generic / contains forget
  signal keywords / very low confidence. Recommendation: forget or
  supersede. Signals: ``len(prop) < 16``, ``confidence < 0.35``,
  keywords ``TODO``, ``FIXME``, ``deprecated``, ``not sure``, ``???``.

* ``recoverable`` (default): mid-confidence, plausible knowledge, no
  clear signals either way. Recommendation: human review.

V1 produces a REPORT only — no mutation. The audit script
``scripts/audit_legacy_corpus.py`` walks the corpus and writes
``audit_legacy_report.json`` for human triage.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .semantic import Fact, SemanticMemory

SEC_PER_DAY = 86400.0


# ---------------------------------------------------------------------------
# Pattern signals
# ---------------------------------------------------------------------------


_VERIFIED_PATTERNS = [
    re.compile(r"bash:[a-z_]+(?::[a-z0-9_]+)*", re.IGNORECASE),
    re.compile(r"file:[^\s]+:\d+"),
    re.compile(r"url:[^\s]+", re.IGNORECASE),
    re.compile(r"https?://(?:arxiv\.org|github\.com|gitlab\.com)/", re.IGNORECASE),
    re.compile(r"\barxiv\.org/(?:abs|html)/\d{4}\.\d{4,5}", re.IGNORECASE),
    re.compile(r"sha(?:256|1)?:[a-f0-9]{6,}", re.IGNORECASE),
    re.compile(r"\bpytest(?:_collect|:)?", re.IGNORECASE),
    re.compile(r"\bexit\s*0\b", re.IGNORECASE),
    re.compile(r"\bcommit\s+[a-f0-9]{6,40}\b", re.IGNORECASE),
]


_FORGET_KEYWORDS = re.compile(
    r"\b(?:todo|fixme|deprecated|not\s+sure|unclear|maybe|placeholder)\b"
    r"|\?{3,}",
    re.IGNORECASE,
)


_MIN_USEFUL_LENGTH = 16
_FORGETTABLE_CONFIDENCE_THRESHOLD = 0.35


def _has_verified_signal(text: str) -> tuple[bool, str]:
    """Return (matched, signal_label) using the first hit only."""
    for pat in _VERIFIED_PATTERNS:
        m = pat.search(text)
        if m:
            return True, m.group(0)
    return False, ""


def _has_forget_signal(text: str, confidence: float) -> tuple[bool, str]:
    if len(text.strip()) < _MIN_USEFUL_LENGTH:
        return True, "short_proposition"
    if confidence < _FORGETTABLE_CONFIDENCE_THRESHOLD:
        return True, "low_confidence"
    m = _FORGET_KEYWORDS.search(text)
    if m:
        return True, f"forget_keyword:{m.group(0)[:20]}"
    return False, ""


# ---------------------------------------------------------------------------
# Dataclass
# ---------------------------------------------------------------------------


@dataclass
class LegacyClassification:
    fact_id: str
    proposition: str
    topic: str
    confidence: float
    age_days: float
    bucket: str
    bucket_reason: str


# ---------------------------------------------------------------------------
# Pure decision
# ---------------------------------------------------------------------------


def classify_legacy_fact(fact: Fact, *, now: float) -> LegacyClassification:
    """Inspect proposition + metadata and pick a bucket.

    Order: verified > forgettable > recoverable. Verified signal wins
    over forget signals because a fact with a real source reference is
    worth preserving even if short or low-confidence.
    """
    text = fact.proposition or ""
    age_days = max(0.0, (now - float(fact.created_at)) / SEC_PER_DAY)

    has_verified, ver_signal = _has_verified_signal(text)
    if has_verified:
        return LegacyClassification(
            fact_id=fact.id, proposition=text, topic=fact.topic,
            confidence=float(fact.confidence), age_days=age_days,
            bucket="verified_on_rereading",
            bucket_reason=f"matched_signal:{ver_signal}",
        )

    has_forget, fg_signal = _has_forget_signal(text, float(fact.confidence))
    if has_forget:
        return LegacyClassification(
            fact_id=fact.id, proposition=text, topic=fact.topic,
            confidence=float(fact.confidence), age_days=age_days,
            bucket="forgettable",
            bucket_reason=fg_signal,
        )

    return LegacyClassification(
        fact_id=fact.id, proposition=text, topic=fact.topic,
        confidence=float(fact.confidence), age_days=age_days,
        bucket="recoverable",
        bucket_reason="no_signal",
    )


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def _select_facts(
    sm: SemanticMemory, *, status_filter: str,
) -> list[Fact]:
    """Pick the legacy population.

    ``status_filter == "any"``: every fact (used on pre-cycle-109
    corpora that don't have a status column).

    ``status_filter == "legacy_unverified"``: only rows whose status
    attribute equals the literal — gracefully handles facts that
    don't carry the attribute (pre-v3 schema) by skipping them.
    """
    all_facts = sm.all()
    if status_filter == "any":
        return all_facts
    return [
        f for f in all_facts
        if getattr(f, "status", None) == status_filter
    ]


def audit_legacy_corpus(
    sm: SemanticMemory,
    *,
    status_filter: str = "legacy_unverified",
    now: float | None = None,
    sample_per_bucket: int = 5,
) -> dict[str, Any]:
    """Walk the legacy population, classify, aggregate.

    Returns::

        {
            "total_classified": N,
            "status_filter": str,
            "bucket_counts": {bucket: count},
            "samples": {bucket: [LegacyClassification, ...]},  # capped
        }
    """
    import time as _t
    now_ts = float(now if now is not None else _t.time())

    selected = _select_facts(sm, status_filter=status_filter)
    bucket_counts: dict[str, int] = {
        "verified_on_rereading": 0,
        "forgettable": 0,
        "recoverable": 0,
    }
    samples: dict[str, list[dict[str, Any]]] = {
        b: [] for b in bucket_counts
    }

    for f in selected:
        cls = classify_legacy_fact(f, now=now_ts)
        bucket_counts[cls.bucket] += 1
        if len(samples[cls.bucket]) < sample_per_bucket:
            samples[cls.bucket].append({
                "fact_id": cls.fact_id,
                "proposition": cls.proposition[:200],
                "topic": cls.topic,
                "confidence": cls.confidence,
                "age_days": round(cls.age_days, 2),
                "bucket_reason": cls.bucket_reason,
            })

    return {
        "total_classified": len(selected),
        "status_filter": status_filter,
        "bucket_counts": bucket_counts,
        "samples": samples,
    }


__all__ = [
    "LegacyClassification",
    "audit_legacy_corpus",
    "classify_legacy_fact",
]
