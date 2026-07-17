"""Persist + roundtrip the write-time grounding score on the Fact (schema v12).

Moonshot #1 brick 2: the score surfaced on GateResult (brick 1) is now stored on the
fact and read back, so retrieval/answering can condition on it. Additive + nullable;
pre-v12 facts read back None.
"""
from __future__ import annotations

from verimem.semantic import Fact, SemanticMemory


def test_grounding_score_roundtrips(tmp_path):
    sm = SemanticMemory(db_path=tmp_path / "semantic" / "semantic.db")
    sm.store(Fact(id="g1", proposition="alpha grounded", topic="t", grounding_score=88.0),
             embed="sync")
    sm.store(Fact(id="g2", proposition="beta ungrounded", topic="t"), embed="sync")  # no score
    assert sm.get("g1").grounding_score == 88.0
    assert sm.get("g2").grounding_score is None


def test_grounding_score_upsert_preserves_known_score(tmp_path):
    """A re-store WITHOUT a score (None) must not wipe a previously-persisted score
    (mirrors the embedding-preserve guard)."""
    sm = SemanticMemory(db_path=tmp_path / "semantic" / "semantic.db")
    sm.store(Fact(id="g1", proposition="alpha", topic="t", grounding_score=72.0), embed="sync")
    sm.store(Fact(id="g1", proposition="alpha v2", topic="t"), embed="sync")  # re-store, no score
    got = sm.get("g1")
    assert got.proposition == "alpha v2"          # update applied
    assert got.grounding_score == 72.0            # score preserved, not nulled


def test_grounding_score_updates_when_provided(tmp_path):
    sm = SemanticMemory(db_path=tmp_path / "semantic" / "semantic.db")
    sm.store(Fact(id="g1", proposition="alpha", topic="t", grounding_score=40.0), embed="sync")
    sm.store(Fact(id="g1", proposition="alpha", topic="t", grounding_score=90.0), embed="sync")
    assert sm.get("g1").grounding_score == 90.0   # newer score wins
