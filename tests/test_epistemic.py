"""TDD — epistemic labels (cortex handoff #1, 2026-07-13): a fact's GUARANTEE
kind, orthogonal to provenance ``status``:

  proven(proof)             machine-checkable proof declared
  unbeaten(bound)           held against every probe up to ``bound`` (grows monotonically)
  refuted(counterexample)   a named counterexample exists — ABSORBING

The lab demo that motivates the axis: coprime6→deficient holds to 10^6 yet dies
at 5391411025 (literature) — "unbeaten(1e6)" and "proven" must never be conflated.
"""
from __future__ import annotations

import pytest

from engram.epistemic import (
    can_transition,
    make_proven,
    make_refuted,
    make_unbeaten,
    parse,
    serialize,
)


def test_constructors_validate():
    assert make_proven("qa:exact_integer_check_PASS")["kind"] == "proven"
    assert make_unbeaten(10**6) == {"kind": "unbeaten", "bound": 10**6}
    r = make_refuted("5391411025")
    assert r["kind"] == "refuted" and r["counterexample"] == "5391411025"
    with pytest.raises(ValueError):
        make_proven("")                    # a proof ref is required, not a vibe
    with pytest.raises(ValueError):
        make_unbeaten(0)                   # a bound must be positive
    with pytest.raises(ValueError):
        make_refuted(" ")                  # a counterexample must be named


def test_parse_serialize_roundtrip_and_garbage():
    lab = make_unbeaten(1000)
    assert parse(serialize(lab)) == lab
    assert parse(None) is None
    assert parse("") is None
    assert parse("not json") is None
    assert parse('{"kind":"nonsense"}') is None      # unknown kind -> unlabeled


def test_transitions_monotone():
    unb6 = make_unbeaten(10**6)
    # first labeling always ok
    assert can_transition(None, unb6)
    # bound grows, never shrinks
    assert can_transition(unb6, make_unbeaten(10**9))
    assert not can_transition(unb6, make_unbeaten(10**3))
    assert not can_transition(unb6, make_unbeaten(10**6))     # no-op not a step
    # upgrade paths
    assert can_transition(unb6, make_proven("qa:proof"))
    assert can_transition(unb6, make_refuted("5391411025"))
    # honest reversal: a "proof" can be found wrong
    assert can_transition(make_proven("qa:p"), make_refuted("cx"))
    # silent downgrade forbidden
    assert not can_transition(make_proven("qa:p"), unb6)


def test_refuted_is_absorbing():
    ref = make_refuted("144")
    assert not can_transition(ref, make_proven("qa:p"))
    assert not can_transition(ref, make_unbeaten(10))
    # a second counterexample may replace the record (still refuted)
    assert can_transition(ref, make_refuted("945"))


def test_store_roundtrip_and_rejected_transition_not_persisted(tmp_path):
    """Integration: the label persists through SQLite; a rejected transition
    leaves the stored label untouched."""
    from engram.semantic import Fact, SemanticMemory
    sm = SemanticMemory(tmp_path / "epi.db")
    fact = Fact(proposition="The nth triangular number is n(n+1)/2.",
                topic="math/triangular")
    sm.store(fact)
    fid = fact.id
    assert sm.set_epistemic(fid, make_unbeaten(10**6)) is True
    got = sm.get(fid)
    assert got.epistemic == make_unbeaten(10**6)
    # regression of the bound is refused and does NOT overwrite
    assert sm.set_epistemic(fid, make_unbeaten(10)) is False
    assert sm.get(fid).epistemic == make_unbeaten(10**6)
    # refutation lands, is absorbing, and survives a reload
    assert sm.set_epistemic(fid, make_refuted("counterexample-n")) is True
    sm2 = SemanticMemory(tmp_path / "epi.db")
    again = sm2.get(fid)
    assert again.epistemic["kind"] == "refuted"
    assert sm2.set_epistemic(fid, make_proven("qa:p")) is False
    # an unknown id is a clean False, not an exception
    assert sm2.set_epistemic("nope-id", make_proven("qa:p")) is False


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
