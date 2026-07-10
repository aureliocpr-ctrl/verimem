"""Per-source trust book (task #17) — pure update rules, TDD.

Laws from the Vivarium transfer (TRANSFER-TO-VERIMEM.md, verified on the
real-gate clone) and this repo's guard-rails (TRUST_CORE.md):

  * consistency channel is USE-INDEPENDENT: it moves on the WRITE stream
    (confirmations/contradictions), so a sunk source that keeps confirming
    accepted values rehabilitates — no absorbing trap;
  * outcome channel exists because consistency alone falls to the trusted
    sleeper (build reputation, then lie unwitnessed);
  * combination is CONSERVATIVE (min): each channel covers the other's
    named hole — averaging would mask it;
  * outcome penalties accept an attenuation weight (stale → reduced blame,
    the attribution-aware hook for task #18);
  * bounded [0,1], neutral prior for unseen sources, dict round-trip for
    future persistence. Pure logic, no I/O, no store dependency.
"""
from __future__ import annotations

import pytest

from engram.source_trust import SourceTrustBook


def test_unseen_source_has_neutral_prior():
    book = SourceTrustBook()
    assert book.trust("never-seen") == pytest.approx(0.5)


def test_confirmation_raises_all_confirmers_contradiction_lowers():
    book = SourceTrustBook()
    book.observe_confirmation(["alice", "bob"])
    assert book.consistency("alice") > 0.5
    assert book.consistency("bob") > 0.5
    book.observe_contradiction("mallory")
    assert book.consistency("mallory") < 0.5


def test_confirmation_requires_two_distinct_sources():
    book = SourceTrustBook()
    book.observe_confirmation(["alice"])          # self-confirmation: no-op
    assert book.consistency("alice") == pytest.approx(0.5)
    book.observe_confirmation(["alice", "alice"])  # duplicates collapse
    assert book.consistency("alice") == pytest.approx(0.5)


def test_sunk_source_rehabilitates_by_confirming():
    """The absorbing-trap killer: consistency moves on the write stream, so
    a source punished into the floor climbs back by agreeing with accepted
    values — WITHOUT ever being 'used' for recall."""
    book = SourceTrustBook()
    for _ in range(5):
        book.observe_contradiction("honest")
    sunk = book.consistency("honest")
    assert sunk < 0.3
    for _ in range(20):
        book.observe_confirmation(["honest", "other"])
    assert book.consistency("honest") > 0.6, "rehabilitation must be possible"


def test_outcome_channel_and_stale_attenuation():
    book = SourceTrustBook()
    book.observe_outcome("fresh_liar", good=False)
    book.observe_outcome("stale_victim", good=False, weight=0.25)
    assert book.outcome("fresh_liar") < book.outcome("stale_victim"), (
        "a stale fact's failure must blame the source LESS than a fresh lie")


def test_trusted_sleeper_is_caught_by_min_combination():
    """Consistency alone scores the sleeper HIGH (it confirms everywhere to
    build reputation); the lie surfaces only in outcomes. min() must let the
    low channel win — averaging would mask the measured 0.89-wrong hole."""
    book = SourceTrustBook()
    for _ in range(10):
        book.observe_confirmation(["sleeper", "honest"])
    for _ in range(4):
        book.observe_outcome("sleeper", good=False)
    assert book.consistency("sleeper") > 0.7
    assert book.trust("sleeper") < 0.4
    assert book.trust("honest") > 0.6


def test_stale_weight_attenuates_by_age():
    """Attribution-aware outcome blame (task #18b, transfer law L3): a fact
    that failed PAST its world's half-life blames the source less — the
    world changed, the source did not lie. Full blame young, half at one
    half-life, floored so blame never vanishes entirely."""
    from engram.source_trust import stale_weight
    assert stale_weight(0.0, half_life_s=100.0) == 1.0
    assert stale_weight(100.0, half_life_s=100.0) == pytest.approx(0.5)
    assert stale_weight(1e9, half_life_s=100.0) == pytest.approx(0.2)
    assert stale_weight(50.0, half_life_s=0.0) == 1.0, (
        "no half-life info → full blame (fail-safe, never silently soft)")


def test_bounds_and_roundtrip():
    book = SourceTrustBook()
    for _ in range(100):
        book.observe_contradiction("bad")
        book.observe_confirmation(["good", "also-good"])
        book.observe_outcome("bad", good=False)
        book.observe_outcome("good", good=True)
    for s in ("bad", "good", "also-good"):
        assert 0.0 <= book.trust(s) <= 1.0
    clone = SourceTrustBook.from_dict(book.to_dict())
    assert clone.trust("bad") == book.trust("bad")
    assert clone.trust("good") == book.trust("good")
