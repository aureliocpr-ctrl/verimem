"""Provenance-INDEPENDENCE in the write-gate consistency channel (Verimem product
priority #1, from the Vivarium collusion/complementarity transfer).

The hole this closes: ``observe_confirmation`` counts DISTINCT source-ID strings, so
N copies of one feed (RSS mirrors, aggregators, LLMs citing one origin) or colluders
with distinct IDs defeat the ">=2 sources" rule — manufactured consensus. With
``require_independent`` the >=2 must be >=2 INDEPENDENT clusters: copies whose report
vectors agree near-perfectly collapse to one witness.

CAVEAT under test (Vivarium v56/P88): raw agreement also merges HONEST sources that
agree because both are right; the numeric guard here is the high threshold + min
shared keys, not a causal deconfound. Behind ENGRAM_SOURCE_TRUST, default OFF.
"""
from __future__ import annotations

from engram.source_trust import SourceTrustBook


def _report_vec(book: SourceTrustBook, sources, vec: dict[str, str]) -> None:
    """Make every source in ``sources`` assert the same (key, value) rows."""
    for s in sources:
        for k, v in vec.items():
            book.record_report(s, k, v)


def test_copies_collapse_to_one_and_cannot_self_confirm():
    b = SourceTrustBook()
    vec = {"k1": "A", "k2": "B", "k3": "C", "k4": "D"}
    _report_vec(b, ["mirror1", "mirror2", "mirror3"], vec)  # 3 copies of one feed
    assert b.independent_clusters(["mirror1", "mirror2", "mirror3"]) == 1
    b.observe_confirmation(["mirror1", "mirror2", "mirror3"], require_independent=True)
    # not confirmed -> no ledger entry -> neutral prior, NOT a raised consistency
    assert b.consistency("mirror1") == 0.5


def test_two_independent_clusters_confirm():
    b = SourceTrustBook()
    _report_vec(b, ["m1", "m2"], {"k1": "A", "k2": "B", "k3": "C", "k4": "D"})  # copies
    _report_vec(b, ["indep"], {"k1": "A", "k2": "X", "k3": "Y", "k4": "Z"})     # differs
    assert b.independent_clusters(["m1", "m2", "indep"]) == 2
    b.observe_confirmation(["m1", "m2", "indep"], require_independent=True)
    assert b.consistency("m1") > 0.5  # independently corroborated -> rises


def test_backward_compatible_without_flag():
    b = SourceTrustBook()
    _report_vec(b, ["m1", "m2", "m3"], {"k1": "A", "k2": "B", "k3": "C"})  # copies
    b.observe_confirmation(["m1", "m2", "m3"])  # no flag -> pre-existing behavior
    assert b.consistency("m1") > 0.5  # 3 distinct IDs still confirm (unchanged)


def test_no_reports_are_all_independent():
    b = SourceTrustBook()  # substrate never fed -> safe fallback == distinct count
    assert b.independent_clusters(["a", "b", "c"]) == 3
    b.observe_confirmation(["a", "b"], require_independent=True)
    assert b.consistency("a") > 0.5


def test_disagreeing_sources_stay_independent():
    b = SourceTrustBook()
    _report_vec(b, ["a"], {"k1": "A", "k2": "B", "k3": "C"})
    _report_vec(b, ["c"], {"k1": "X", "k2": "Y", "k3": "Z"})  # total disagreement
    assert b.independent_clusters(["a", "c"]) == 2


def test_too_few_shared_keys_not_called_copies():
    b = SourceTrustBook()
    # identical but only ONE co-reported key: below _COPY_MIN_SHARED -> independent
    b.record_report("a", "k1", "same")
    b.record_report("c", "k1", "same")
    assert b.independent_clusters(["a", "c"]) == 2


def test_collusion_numeric_gap_naive_vs_independent():
    """The headline number: naive counting confirms a false claim from 3 colluding
    copies; independence blocks it (the manufactured-consensus attack)."""
    naive = SourceTrustBook()
    vec = {"k1": "A", "k2": "B", "k3": "C"}
    _report_vec(naive, ["c1", "c2", "c3"], vec)
    naive.observe_confirmation(["c1", "c2", "c3"])                      # no flag
    assert naive.consistency("c1") > 0.5                               # naive: fooled

    guarded = SourceTrustBook()
    _report_vec(guarded, ["c1", "c2", "c3"], vec)
    guarded.observe_confirmation(["c1", "c2", "c3"], require_independent=True)
    assert guarded.consistency("c1") == 0.5                            # guarded: held
