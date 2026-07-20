"""The OUTCOME channel's application API — Memory.report_outcome.

Reporting a fact FAILED in use penalizes its source's outcome reputation AND marks the
fact's value audit-revealed false (the do-operator that unlocks the deconfounded
independence). Success raises the source. Unknown fact -> False.
"""
from __future__ import annotations

from verimem.client import Memory
from verimem.source_trust import reset_book_cache


def test_reported_failure_penalizes_source(tmp_path):
    reset_book_cache()
    mem = Memory(tmp_path / "m.db")
    r = mem.add("The sky is green.", topic="observational/sky", verified_by=["source-doc:liar:1"])
    assert mem.report_outcome(r["id"], good=False) is True
    assert mem.source_trust("liar") < 0.5          # outcome channel bit through


def test_reported_success_does_not_penalize(tmp_path):
    reset_book_cache()
    mem = Memory(tmp_path / "m.db")
    r = mem.add("The sky is blue.", topic="observational/sky", verified_by=["source-doc:honest:1"])
    assert mem.report_outcome(r["id"], good=True) is True
    assert mem.source_trust("honest") >= 0.5


def test_report_outcome_unknown_fact_returns_false(tmp_path):
    reset_book_cache()
    mem = Memory(tmp_path / "m.db")
    assert mem.report_outcome("does-not-exist", good=False) is False


def test_failure_marks_the_value_false_for_deconfound(tmp_path):
    """The audit anchor: after a reported failure, the fact's (topic, proposition) is
    marked false, so two colluders who both asserted it register a collusion signal."""
    reset_book_cache()
    mem = Memory(tmp_path / "m.db")
    prop = "The code is 1234."
    a = mem.add(prop, topic="k/code", verified_by=["source-doc:c0:1"])
    mem.add(prop, topic="k/code", verified_by=["source-doc:c1:1"])
    mem.report_outcome(a["id"], good=False)         # audit reveals the value false
    book = mem._source_trust_book()
    book.record_report("c0", "k/code", prop)
    book.record_report("c1", "k/code", prop)
    # both co-admit an audited-false value -> collusion signal fires (need a 2nd key)
    book.mark_false("k/code2", prop)
    book.record_report("c0", "k/code2", prop)
    book.record_report("c1", "k/code2", prop)
    assert book.independent_clusters(["c0", "c1"], deconfounded=True) == 1
