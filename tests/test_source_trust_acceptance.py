"""Independence-aware ACCEPTANCE (SourceTrustBook.accept_value) — the primitive the
real-path reproduction (benchmark/independence_validation.py) proved necessary: the
'accepted' value must be the one with the most INDEPENDENT witnesses, not raw sources,
so a write-majority cartel cannot win the acceptance vote and invert honest trust.
"""
from __future__ import annotations

from verimem.source_trust import SourceTrustBook, auto_confirm_agreement


def _vec(b, sources, vec):
    for s in sources:
        for k, v in vec.items():
            b.record_report(s, k, v)


def _seed_cartel_and_honest(b):
    """8 colluders with identical multi-key history (copies) + 2 honest with diverse
    history — the report vectors independence needs to tell them apart."""
    cartel = [f"c{i}" for i in range(8)]
    for c in cartel:
        for k in ("s1", "s2", "s3"):
            b.record_report(c, k, "F")
    b.record_report("h0", "s1", "T"); b.record_report("h0", "ax", "1")
    b.record_report("h1", "s1", "T"); b.record_report("h1", "bx", "2")
    return cartel


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


def test_auto_confirm_independence_beats_majority_cartel():
    b = SourceTrustBook()
    cartel = _seed_cartel_and_honest(b)
    reports = {**{c: "F" for c in cartel}, "h0": "T", "h1": "T"}
    r = auto_confirm_agreement(b, "s4", reports, independence=True)
    assert r["accepted"] == "T"                       # honest value wins on independence
    assert set(r["confirmed"]) == {"h0", "h1"}
    assert set(r["contradicted"]) == set(cartel)
    assert b.consistency("h0") > 0.5                  # honest rise
    assert b.consistency("c0") < 0.5                  # cartel contradicted


def test_auto_confirm_naive_is_fooled_by_the_cartel():
    b = SourceTrustBook()
    cartel = _seed_cartel_and_honest(b)
    reports = {**{c: "F" for c in cartel}, "h0": "T", "h1": "T"}
    r = auto_confirm_agreement(b, "s4", reports, independence=False)
    assert r["accepted"] == "F"                        # raw majority -> cartel wins
    assert set(r["contradicted"]) == {"h0", "h1"}      # honest wrongly contradicted


def test_auto_confirm_single_source_no_confirmation():
    b = SourceTrustBook()
    r = auto_confirm_agreement(b, "s1", {"solo": "X"}, independence=True)
    assert r == {"accepted": None, "confirmed": [], "contradicted": []}
