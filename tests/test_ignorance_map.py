"""TDD — the ignorance map (Vivarium P83 / cortex cognition): not just "I don't
know" but "here is WHAT I'm missing to answer". For each failed query the map
names the ignorance CLASS and what would cure it — the active complement of
abstention (P83 in the lab: diagnosing the missing sub-competence made
learning it 6.2× cheaper than blind exploration).
"""
from __future__ import annotations

import pytest

from engram.ignorance_map import ignorance_map


@pytest.fixture()
def mem(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGRAM_SOURCE_TRUST", "0")
    monkeypatch.setenv("ENGRAM_RECONCILE_ON_WRITE", "0")
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", "0")
    from engram.client import Memory
    return Memory(tmp_path / "ig.db")


def test_classes_no_evidence_conflict_and_answerable(mem):
    mem.add("Rex is a labrador.", topic="pets", verified_by=["source-doc:alice:t1"])
    mem.add("Rex is a poodle.", topic="pets", verified_by=["source-doc:bob:t1"])
    mem.add("Milo is a cat.", topic="pets", verified_by=["source-doc:alice:t2"])
    # Derive the floor from the clean hit's OWN score so the class contract is
    # tested independent of the embedder's absolute scale (the suite runs a
    # deterministic stub embedder, not the production e5 — conftest).
    milo_top = mem.search("What is Milo?", k=3)[0]["score"]
    floor = milo_top - 0.01
    out = ignorance_map(mem, [
        "What is the capital of Mars?",      # nothing remotely relevant
        "What breed is Rex?",                # two voices disagree
        "What is Milo?",                     # clean answer, clears its own floor
    ], floor=floor)
    by_q = {r["query"]: r for r in out["queries"]}
    assert by_q["What is the capital of Mars?"]["class"] in ("no_evidence", "below_floor")
    rex = by_q["What breed is Rex?"]
    assert rex["class"] == "conflict"                  # conflict beats the floor
    assert len(rex["conflicting_ids"]) == 2
    assert "independent source" in rex["what_would_help"]
    assert by_q["What is Milo?"]["class"] == "answerable"
    # the summary counts every class it saw — nothing silently dropped
    assert sum(out["by_class"].values()) == 3


def test_below_floor_names_the_gap(mem):
    mem.add("The quarterly report mentions revenue growth.", topic="w",
            verified_by=["source-doc:kb:t1"])
    out = ignorance_map(mem, ["Che tempo fa domani a Roma?"], floor=0.99)
    r = out["queries"][0]
    assert r["class"] in ("below_floor", "no_evidence")
    assert r["top_score"] is None or r["top_score"] < 0.99


def test_quarantined_only_is_its_own_class(mem, monkeypatch):
    res = mem.add("The migration is done and everything works perfectly.",
                  topic="w", verified_by=["source-doc:dev:t1"])
    # if the gate quarantined it (dev-claim), default recall sees nothing —
    # but the ignorance map must say WHY: evidence exists, quarantined.
    if res.get("status") == "quarantined":
        out = ignorance_map(mem, ["Is the migration done?"], floor=0.5)
        assert out["queries"][0]["class"] == "quarantined_only"
        assert "quarantined" in out["queries"][0]["what_would_help"]
    else:
        pytest.skip("gate admitted the claim in this configuration")


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
