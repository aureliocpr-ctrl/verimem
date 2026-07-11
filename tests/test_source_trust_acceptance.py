"""Independence-aware ACCEPTANCE (SourceTrustBook.accept_value) — the primitive the
real-path reproduction (benchmark/independence_validation.py) proved necessary: the
'accepted' value must be the one with the most INDEPENDENT witnesses, not raw sources,
so a write-majority cartel cannot win the acceptance vote and invert honest trust.
"""
from __future__ import annotations

from engram.source_trust import SourceTrustBook


def _vec(b, sources, vec):
    for s in sources:
        for k, v in vec.items():
            b.record_report(s, k, v)


def test_honest_pair_beats_majority_cartel():
    b = SourceTrustBook()
    cartel = [f"c{i}" for i in range(8)]
    _vec(b, cartel, {"k1": "F", "k2": "F", "k3": "F", "k4": "F"})   # 8 copies -> 1 cluster
    b.record_report("h0", "k1", "T"); b.record_report("h0", "k5", "a")
    b.record_report("h0", "k6", "b")
    b.record_report("h1", "k1", "T"); b.record_report("h1", "k7", "c")
    b.record_report("h1", "k8", "d")                               # h0,h1 share <3 keys
    accepted = b.accept_value({"F": cartel, "T": ["h0", "h1"]})
    assert accepted == ("T", ["h0", "h1"])                         # 2 indep > 1 cartel


def test_cartel_alone_cannot_self_accept():
    b = SourceTrustBook()
    cartel = [f"c{i}" for i in range(6)]
    _vec(b, cartel, {"k1": "F", "k2": "F", "k3": "F"})
    assert b.accept_value({"F": cartel}) is None                   # 1 witness < 2


def test_single_independently_corroborated_value_accepted():
    b = SourceTrustBook()
    b.record_report("a", "ka", "X"); b.record_report("b", "kb", "X")   # disjoint -> indep
    assert b.accept_value({"X": ["a", "b"]}) == ("X", ["a", "b"])


def test_tie_on_independent_witnesses_accepts_neither():
    b = SourceTrustBook()
    for s, k in (("a", "ka"), ("b", "kb"), ("p", "kp"), ("q", "kq")):
        b.record_report(s, k, "v")                                 # all mutually indep
    assert b.accept_value({"A": ["a", "b"], "B": ["p", "q"]}) is None


def test_deconfound_rescues_dense_honest_agreement():
    b = SourceTrustBook()
    # two honest sources reporting IDENTICAL true values -> raw agreement merges them
    _vec(b, ["h0", "h1"], {"k1": "T", "k2": "T", "k3": "T"})
    assert b.accept_value({"T": ["h0", "h1"]}) is None             # raw: false-merged -> rejected
    # deconfounded: their agreement is on truth (no audit anchor) -> stay independent
    assert b.accept_value({"T": ["h0", "h1"]}, deconfounded=True) == ("T", ["h0", "h1"])
