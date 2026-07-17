"""Deconfounded independence (Vivarium P88) — the audit is the do-operator.

Raw report agreement is CONFOUNDED by shared truth: honest sources that agree
because both are RIGHT false-merge (the documented caveat on the raw signal).
Conditioning on audit-revealed-FALSE co-admission isolates real collusion — honest
peers reject falsehoods, colluders admit them. This concatenates the other
instance's cartel_kill_v56 result into the write-gate.
"""
from __future__ import annotations

from verimem.source_trust import SourceTrustBook


def test_raw_merges_honest_but_deconfounded_does_not():
    """The caveat, fixed: two honest sources reporting the same TRUE values look like
    copies to raw agreement (merged), but stay INDEPENDENT under deconfounding."""
    b = SourceTrustBook()
    truth = {"k1": "T1", "k2": "T2", "k3": "T3", "k4": "T4"}
    for s in ("honest_a", "honest_b"):
        for k, v in truth.items():
            b.record_report(s, k, v)
    assert b.independent_clusters(["honest_a", "honest_b"]) == 1                 # raw: confounded
    assert b.independent_clusters(["honest_a", "honest_b"], deconfounded=True) == 2


def test_deconfounded_merges_colluders_who_co_admit_falsehoods():
    b = SourceTrustBook()
    lie = {"k1": "F1", "k2": "F2", "k3": "F3"}
    for s in ("cartel_a", "cartel_b"):
        for k, v in lie.items():
            b.record_report(s, k, v)
    for k, v in lie.items():
        b.mark_false(k, v)                       # the audit reveals these false
    assert b.independent_clusters(["cartel_a", "cartel_b"], deconfounded=True) == 1


def test_honest_rejecter_not_merged_with_admitter():
    b = SourceTrustBook()
    lie = {"k1": "F1", "k2": "F2", "k3": "F3"}
    for k, v in lie.items():
        b.record_report("admitter", k, v)        # admits the falsehood
        b.record_report("rejecter", k, "true-" + k)  # rejects it (reports otherwise)
        b.mark_false(k, v)
    assert b.independent_clusters(["admitter", "rejecter"], deconfounded=True) == 2


def test_needs_min_shared_audited_false():
    b = SourceTrustBook()
    b.record_report("a", "k1", "F1")
    b.record_report("c", "k1", "F1")
    b.mark_false("k1", "F1")                      # only ONE shared audited-false key
    assert b.independent_clusters(["a", "c"], deconfounded=True) == 2


def test_fail_open_without_audit_anchor():
    b = SourceTrustBook()
    vec = {"k1": "x", "k2": "y", "k3": "z"}
    for s in ("a", "c"):
        for k, v in vec.items():
            b.record_report(s, k, v)
    # no mark_false -> no anchor -> nobody merges (fail-open, never a silent false-merge)
    assert b.independent_clusters(["a", "c"], deconfounded=True) == 2
