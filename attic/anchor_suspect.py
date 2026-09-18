"""ANCHOR-SUSPECT — bidirectional trust (cortex/Vivarium GRANDE-3 transfer).

VeriMem's write-gate has always treated the ANCHOR — existing memory, the
majority, the "ground truth" the store already holds — as infallible: a new
claim that disagrees with it is the thing that gets rejected. GRANDE-3
falsified that on real data: a public dataset had a record mislabeled (Radon
tagged as an Alkali Metal) and the high-trust generator that contradicted it
was RIGHT. Localized disagreement from a trusted source is the signature of a
DATA-QUALITY defect, not of a false claim.

This formalizes the pattern into a measurable, hermetic detector: when a source
of trust >= ``trust_floor`` disagrees with the anchor on only a FEW records
(<= ``max_frac`` of a well-supported set), the RECORDS become suspect (candidate
corruption / staleness) — not the source's assertion. Many disagreements instead
refute the claim; a low-trust source never gets to suspect the store.

It is ADVISORY: it returns the suspected record ids + a reason and the consumer
(quarantine, re-verify, down-weight) decides. Any AUTO-action a caller wires on
top is gated by ``ENGRAM_ANCHOR_SUSPECT`` (default off), so behaviour is
unchanged until the signal is validated on a real corpus — the standing rule for
a new trust mechanism. Verified against injected corruptions of known ground
truth, so precision/recall are real numbers.
"""
from __future__ import annotations

import os
from collections.abc import Hashable, Iterable, Mapping

__all__ = [
    "detect_suspect_records", "violating_records", "precision_recall",
    "suspects_for_source", "enabled",
    "INSUFFICIENT_SUPPORT", "SOURCE_NOT_TRUSTED", "VALUE_HOLDS",
    "RECORDS_SUSPECTED", "VALUE_REFUTED",
]

#: reasons (a stable vocabulary the consumer can branch on)
INSUFFICIENT_SUPPORT = "insufficient-support"
SOURCE_NOT_TRUSTED = "source-not-trusted"
VALUE_HOLDS = "value-holds"
RECORDS_SUSPECTED = "records-suspected"
VALUE_REFUTED = "value-refuted"

_TRUST_FLOOR = 0.8
_MAX_FRAC = 0.05
_MIN_SUPPORT = 20


def enabled() -> bool:
    """Gate for AUTO-action built on the detector (e.g. auto-quarantine of the
    suspected records). The detector is always callable; only automatic
    side effects wait on ``ENGRAM_ANCHOR_SUSPECT`` so the default is byte-for-byte
    unchanged behaviour."""
    return os.getenv("ENGRAM_ANCHOR_SUSPECT", "").strip().lower() in {
        "1", "true", "yes", "on"}


def violating_records(records: Mapping[Hashable, object],
                      trusted_value: object) -> list:
    """Record ids whose stored value disagrees with the trusted assertion."""
    tv = str(trusted_value)
    return [rid for rid, val in records.items() if str(val) != tv]


def _classify(support: int, violations: list, source_trust: float, *,
              trust_floor: float, max_frac: float,
              min_support: int) -> tuple[list, str]:
    """The shared gate over a support count and its violating ids."""
    if support < min_support:
        return [], INSUFFICIENT_SUPPORT
    if source_trust < trust_floor:
        # below the floor: believe the anchor — the claim is simply wrong, and we
        # emit NO data-corruption flags (a distrusted source cannot indict the store)
        return [], SOURCE_NOT_TRUSTED
    if not violations:
        return [], VALUE_HOLDS
    if len(violations) <= max_frac * support:
        return list(violations), RECORDS_SUSPECTED    # few localized = data error
    return [], VALUE_REFUTED                           # many = the claim is wrong


def detect_suspect_records(records: Mapping[Hashable, object],
                           trusted_value: object, source_trust: float, *,
                           trust_floor: float = _TRUST_FLOOR,
                           max_frac: float = _MAX_FRAC,
                           min_support: int = _MIN_SUPPORT) -> tuple[list, str]:
    """Bidirectional-trust gate. ``records`` maps record-id -> stored value for one
    subject; ``trusted_value`` is what a source of trust ``source_trust`` asserts is
    correct. Returns ``(suspected_ids, reason)``."""
    return _classify(len(records), violating_records(records, trusted_value),
                     source_trust, trust_floor=trust_floor, max_frac=max_frac,
                     min_support=min_support)


def precision_recall(flagged: Iterable, truly_corrupt: Iterable) -> tuple[float, float]:
    """Real numbers over an injected ground truth (validation aid)."""
    f, t = set(flagged), set(truly_corrupt)
    tp = len(f & t)
    precision = tp / len(f) if f else 0.0
    recall = tp / len(t) if t else 0.0
    return round(precision, 3), round(recall, 3)


def suspects_for_source(book, trusted_source: str,
                        anchor: Mapping[Hashable, object], *,
                        trust: float | None = None,
                        trust_floor: float = _TRUST_FLOOR,
                        max_frac: float = _MAX_FRAC,
                        min_support: int = _MIN_SUPPORT) -> tuple[list, str]:
    """Integration over a ``SourceTrustBook``: a trusted source has asserted values
    across many subject keys (its report vector); ``anchor`` is the store's currently
    accepted value per key. Flag the FEW keys where the trusted source disagrees with
    the anchor as suspected records.

    ``trust`` overrides ``book.trust(trusted_source)`` (test/introspection seam);
    otherwise the source's real, earned trust decides. Read-only: it mutates nothing."""
    reports = getattr(book, "_reports", {}).get(trusted_source, {})
    # records = the keys this source reported that the anchor also covers
    keys = [k for k in reports if k in anchor]
    violations = [k for k in keys if str(reports[k]) != str(anchor[k])]
    st = book.trust(trusted_source) if trust is None else float(trust)
    return _classify(len(keys), violations, st, trust_floor=trust_floor,
                     max_frac=max_frac, min_support=min_support)
