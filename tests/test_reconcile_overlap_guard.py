"""Iter 4 — precision dial on the NLI conflict path.

The local NLI judge over-calls CONTRADICTION on ~6.7% of same-entity DIFFERENT-
attribute (complementary) pairs (measured, HaluMem thr 0.9), which then wrongly
supersede -> delete truth. A content-token overlap floor filters them: a same-
attribute VALUE conflict shares subject+attribute (high overlap), a complementary
pair shares little beyond the entity. This is a precision/recall DIAL (verified
frontier: 0.0 -> recall 0.2833/false-compl 0.0667; 0.2 -> ~0.20/~0.008), NOT a free
win, so it is default OFF (floor 0 = unchanged) and opt-in per deployment.
"""
from __future__ import annotations

from verimem.semantic_conflict import Relation
from verimem.truth_reconciliation import _content_overlap, _is_conflict


class _Contra:
    """A judge that always says CONTRADICTION — isolates the overlap guard."""

    def classify(self, a, b):
        return Relation.CONTRADICTION


def test_overlap_guard_rejects_low_overlap_complementary(monkeypatch) -> None:
    monkeypatch.setenv("ENGRAM_RECONCILE_MIN_OVERLAP", "0.2")
    a = "Taylor David shared anecdotes about the museum trip"
    b = "Taylor David launched a new consultancy company"   # same person, diff attribute
    assert _content_overlap(a, b) < 0.2
    assert _is_conflict(a, b, _Contra()) is False   # NLI says contra, guard rejects


def test_overlap_guard_keeps_value_conflict(monkeypatch) -> None:
    monkeypatch.setenv("ENGRAM_RECONCILE_MIN_OVERLAP", "0.2")
    a = "the capital of Zorvia is Helmsford"
    b = "the capital of Zorvia is Brantol"                  # same attribute, diff value
    assert _content_overlap(a, b) >= 0.2
    assert _is_conflict(a, b, _Contra()) is True


def test_default_floor_off_is_byte_identical(monkeypatch) -> None:
    monkeypatch.delenv("ENGRAM_RECONCILE_MIN_OVERLAP", raising=False)
    a = "Taylor David shared anecdotes about the museum trip"
    b = "Taylor David launched a new consultancy company"
    # floor 0 -> the NLI verdict passes through unchanged (no guard)
    assert _is_conflict(a, b, _Contra()) is True


def test_content_overlap_symmetric_and_bounded() -> None:
    a, b = "the port is 8080", "the port is 9090"
    assert _content_overlap(a, b) == _content_overlap(b, a)
    assert 0.0 <= _content_overlap(a, b) <= 1.0
    assert _content_overlap("", "anything") == 0.0
