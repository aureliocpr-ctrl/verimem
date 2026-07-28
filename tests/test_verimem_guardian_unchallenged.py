""""Unchallenged" must mean "I looked and found no rival", not "I could not look".

`correct_read` groups rival facts using the composer's copula parse, so it can
only compare facts shaped like "X is a Y." When the top hit is not copula there
are no contenders to gather, the fact is returned alone, and the receipt reads
``reason="unchallenged"`` — a positive claim that the store holds nothing
against this answer.

Measured on the real corpus (2026-07-28, a consistent copy of ~/.engram):
0 of 4208 live facts have copula structure; the median proposition is 814
characters of prose. Five ordinary questions returned five ACCEPT /
"unchallenged" / evidence=1. The guardian is wired in production at
GET /v1/correct, so that word reaches real callers.

This does NOT teach the guardian to compare prose — that is a different and much
larger change, and pretending otherwise would be the same overclaim one level
down. It separates the two cases the receipt was conflating, exactly as the gate
already does with its L4-skipped advisory ("say so out loud, NEVER a silent
skip"): the verdict is unchanged, the caller is told which of the two it got.
"""
from __future__ import annotations

import pytest

from verimem.guardian import correct_read


@pytest.fixture()
def mem(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGRAM_SOURCE_TRUST", "0")
    monkeypatch.setenv("ENGRAM_RECONCILE_ON_WRITE", "0")
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", "0")
    monkeypatch.setenv("ENGRAM_SEMANTIC_CONFLICT", "0")
    from verimem.client import Memory
    return Memory(tmp_path / "u.db")


PROSE = ("The migration ran on the staging cluster and the read path was "
         "switched over at 14:00 with no downtime reported by the operators.")


def test_prose_is_not_reported_as_unchallenged(mem):
    """A fact the guardian cannot compare must not be called uncontested."""
    mem.add(PROSE, topic="ops", verified_by=["source-doc:runbook:t1"])
    out = correct_read(mem, "what happened during the migration?")
    assert out["verdict"] == "ACCEPT"
    assert out["reason"] != "unchallenged", (
        "the guardian never gathered a contender — it must not claim there "
        "was none")
    assert "not comparable" in out["reason"], out["reason"]


def test_a_copula_fact_with_no_rival_is_still_unchallenged(mem):
    """Where the comparison CAN happen and finds nothing, the word is earned."""
    mem.add("Rex is a labrador.", topic="pets", verified_by=["source-doc:a:t1"])
    out = correct_read(mem, "What breed is Rex?")
    assert out["verdict"] == "ACCEPT"
    assert out["reason"] == "unchallenged"


def test_the_answer_is_unchanged_either_way(mem):
    """Only the receipt changes: the same fact is still served."""
    res = mem.add(PROSE, topic="ops", verified_by=["source-doc:runbook:t1"])
    out = correct_read(mem, "what happened during the migration?")
    assert out["served_id"] == res["id"]
    assert out["answer"] == PROSE
    assert out["evidence"] == [res["id"]]


def test_conflict_detection_is_untouched(mem):
    """The guard must not leak into the path that does compare."""
    mem.add("Rex is a labrador.", topic="pets", verified_by=["source-doc:a:t1"])
    mem.add("Rex is a poodle.", topic="pets", verified_by=["source-doc:b:t1"])
    out = correct_read(mem, "What breed is Rex?")
    assert out["verdict"] == "ABSTAIN"
    assert out["reason"] == "conflict_without_epistemic_winner"
