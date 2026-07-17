"""ANCHOR-SUSPECT (bidirectional trust) — cortex/Vivarium GRANDE-3 transfer.

VeriMem's gate assumed the anchor (existing memory / majority) infallible.
GRANDE-3 falsified that on real data: a public dataset had a mislabeled record
and the high-trust source was RIGHT. The detector flags the FEW, LOCALIZED
records a trusted source disagrees with as candidate corruption — not the claim.
Verified with injected corruptions of KNOWN ground truth, so precision/recall
are real numbers.
"""
from __future__ import annotations

from verimem.anchor_suspect import (
    INSUFFICIENT_SUPPORT,
    RECORDS_SUSPECTED,
    SOURCE_NOT_TRUSTED,
    VALUE_HOLDS,
    VALUE_REFUTED,
    detect_suspect_records,
    precision_recall,
    suspects_for_source,
)


def _records(n, corrupt_ids, good="A", bad="B"):
    """n records that should all read ``good``; ``corrupt_ids`` read ``bad``."""
    return {i: (bad if i in corrupt_ids else good) for i in range(n)}


def test_few_localized_violations_of_a_trusted_value_flag_the_records():
    corrupt = {7, 41, 88}
    rec = _records(100, corrupt)
    flagged, reason = detect_suspect_records(rec, "A", source_trust=0.9)
    assert reason == RECORDS_SUSPECTED
    assert set(flagged) == corrupt
    # real numbers over the injected ground truth
    assert precision_recall(flagged, corrupt) == (1.0, 1.0)


def test_low_trust_source_believes_the_anchor():
    """A source below the trust floor does NOT get to suspect the store — its
    disagreement just means its own claim is wrong (no false data-corruption flags)."""
    rec = _records(100, {7, 41, 88})
    flagged, reason = detect_suspect_records(rec, "A", source_trust=0.5)
    assert reason == SOURCE_NOT_TRUSTED and flagged == []


def test_many_violations_refute_the_value_not_the_records():
    """When a trusted source disagrees with MANY records the claim is genuinely
    wrong (or the domain shifted) — do not flag a third of the store as corrupt."""
    rec = _records(100, set(range(30)))
    flagged, reason = detect_suspect_records(rec, "A", source_trust=0.95)
    assert reason == VALUE_REFUTED and flagged == []


def test_no_violations_is_value_holds():
    rec = _records(100, set())
    flagged, reason = detect_suspect_records(rec, "A", source_trust=0.95)
    assert reason == VALUE_HOLDS and flagged == []


def test_thin_support_never_fires():
    """Below min_support 'few of many' is meaningless — never flag on thin evidence."""
    rec = _records(5, {1})
    flagged, reason = detect_suspect_records(rec, "A", source_trust=0.95)
    assert reason == INSUFFICIENT_SUPPORT and flagged == []


def test_boundary_is_inclusive_at_max_frac():
    # 5% of 100 = 5 violations exactly -> still suspected (<=), 6 -> refuted
    assert detect_suspect_records(_records(100, set(range(5))), "A",
                                  source_trust=0.9)[1] == RECORDS_SUSPECTED
    assert detect_suspect_records(_records(100, set(range(6))), "A",
                                  source_trust=0.9)[1] == VALUE_REFUTED


def test_precision_recall_partial():
    # flag 4 where only 3 are truly corrupt -> precision 0.75, recall 1.0
    assert precision_recall([1, 2, 3, 9], [1, 2, 3]) == (0.75, 1.0)
    assert precision_recall([], [1]) == (0.0, 0.0)


def test_suspects_for_source_over_a_trust_book():
    """Integration: a trusted source asserts a value across MANY subject keys; the
    anchor (store's accepted value per key) disagrees on a FEW → those keys are the
    suspected records. Reads the SourceTrustBook's own report substrate."""
    from verimem.source_trust import SourceTrustBook

    book = SourceTrustBook()
    anchor = {}
    for i in range(40):
        key = f"element/{i}/type"
        book.record_report("curated-lab", key, "metal")   # the trusted source's view
        anchor[key] = "metal"
    # inject 2 anchor corruptions (the store is wrong on 2 keys)
    anchor["element/5/type"] = "gas"
    anchor["element/23/type"] = "gas"

    flagged, reason = suspects_for_source(book, "curated-lab", anchor, trust=0.9)
    assert reason == RECORDS_SUSPECTED
    assert set(flagged) == {"element/5/type", "element/23/type"}


def test_suspects_for_source_untrusted_source_defers_to_anchor():
    from verimem.source_trust import SourceTrustBook

    book = SourceTrustBook()
    anchor = {}
    for i in range(40):
        key = f"k/{i}"
        book.record_report("rando", key, "x")
        anchor[key] = "x"
    anchor["k/5"] = "y"
    # a fresh/unknown source is NEUTRAL (0.5) < floor -> no suspicion
    flagged, reason = suspects_for_source(book, "rando", anchor)
    assert reason == SOURCE_NOT_TRUSTED and flagged == []
