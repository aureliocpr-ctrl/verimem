"""How much of the corpus the moat actually judged has to be visible.

`verimem stats` reports what the gate DID — admitted, quarantined, rejected,
abstained, live facts by status — under the line "The numbers competitors don't
show". The one number it did not show is the one that bounds all the others:
how many stored facts were ever put through the entailment moat.

Measured on the real corpus (2026-07-28, consistent copy of ~/.engram):

    6414 facts, 0 with a grounding_score  ->  0.0%
    490 of 6414 (7.6%) carry provenance at all

Verified not to be a persistence artefact: a fact written WITH a source stores
97.77 in that column, one written without stores NULL. So the moat — which
separates an entailed fact at 97.8 from a contradicted one at 0.25 — had never
run on this corpus, and nothing in the product said so. `epistemic_health`
computes exactly this (`provenance_coverage`, documented as bounding "how much
of the corpus is even grounding-auditable") and has no production caller.

The counting part needs no judge and no LLM call: it is a SQL count over a
column already persisted on every write. What it buys is that an operator can
see the moat is idle instead of assuming it is working.
"""
from __future__ import annotations

import pytest


@pytest.fixture()
def mem(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGRAM_SOURCE_TRUST", "0")
    monkeypatch.setenv("ENGRAM_RECONCILE_ON_WRITE", "0")
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", "0")
    from verimem.client import Memory
    return Memory(tmp_path / "cov.db")


def test_stats_report_how_much_of_the_corpus_the_moat_judged(mem):
    mem.add("Rex is a labrador.", topic="w",
            source="The kennel registry lists Rex as a labrador.")
    mem.add("Milo is a cat.", topic="w")                       # no source
    cov = mem.trust_stats().get("moat")
    assert cov is not None, "trust_stats must report the moat's own coverage"
    assert cov["facts"] == 2
    assert cov["grounded"] == 1, "one write carried a source and was judged"
    assert cov["coverage"] == 0.5


def test_a_corpus_the_moat_never_saw_reads_zero_not_missing(mem):
    """The honest number for an unjudged corpus is 0.0, never a blank.

    Distinct propositions on purpose: near-identical writes are DEDUPLICATED,
    so three variations on one sentence land as one fact and the count would
    measure the dedup rather than the coverage.
    """
    mem.add("The staging cluster was rebuilt on Tuesday.", topic="w")
    mem.add("Payroll exports moved to the new bucket.", topic="w")
    mem.add("Nadia joined the platform team in March.", topic="w")
    cov = mem.trust_stats()["moat"]
    assert cov["facts"] == 3
    assert cov["grounded"] == 0
    assert cov["coverage"] == 0.0


def test_provenance_is_counted_separately_from_grounding(mem):
    """verified_by is provenance, NOT a grounding run — the two must not be
    conflated in the report any more than they are in the write path."""
    mem.add("Rex is a labrador.", topic="w",
            verified_by=["source-doc:kennel:t1"])              # ref, no text
    cov = mem.trust_stats()["moat"]
    assert cov["with_provenance"] == 1
    assert cov["grounded"] == 0, (
        "a verified_by ref does not run the moat, so it must not be counted "
        "as if it had")


def test_an_empty_store_does_not_divide_by_zero(mem):
    cov = mem.trust_stats()["moat"]
    assert cov["facts"] == 0
    assert cov["coverage"] == 0.0
