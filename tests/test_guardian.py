"""TDD — guardian.correct at the read-path (cortex handoff piece #1).

Not just block-or-abstain: when the store CONTAINS a better-guaranteed truth
about the same subject, the read returns it as a CORRECTION with both facts
cited. Verdicts: ACCEPT (top hit stands) / CORRECT (a better-labeled fact on
the same subject wins) / ABSTAIN (a real conflict with no epistemic winner —
never pick silently).
"""
from __future__ import annotations

import pytest

from engram.epistemic import make_proven, make_refuted
from engram.guardian import correct_read


@pytest.fixture()
def mem(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGRAM_SOURCE_TRUST", "0")
    monkeypatch.setenv("ENGRAM_RECONCILE_ON_WRITE", "0")
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", "0")
    from engram.client import Memory
    return Memory(tmp_path / "g.db")


def test_accept_when_unchallenged(mem):
    mem.add("Rex is a labrador.", topic="pets", verified_by=["source-doc:alice:t1"])
    out = correct_read(mem, "What is Rex?")
    assert out["verdict"] == "ACCEPT"
    assert "labrador" in out["answer"]


def test_correct_when_better_labeled_fact_conflicts(mem):
    a = mem.add("Rex is a labrador.", topic="pets", verified_by=["source-doc:alice:t1"])
    b = mem.add("Rex is a poodle.", topic="pets", verified_by=["source-doc:vet:t2"])
    assert mem.semantic.set_epistemic(b["id"], make_proven("qa:vet_registry_check_PASS"))
    out = correct_read(mem, "What breed is Rex?")
    assert out["verdict"] == "CORRECT"
    assert "poodle" in out["answer"]
    assert set(out["evidence"]) >= {a["id"], b["id"]}     # both sides cited
    assert "proven" in out["reason"]


def test_abstain_on_unresolvable_conflict(mem):
    mem.add("Rex is a labrador.", topic="pets", verified_by=["source-doc:alice:t1"])
    mem.add("Rex is a poodle.", topic="pets", verified_by=["source-doc:bob:t1"])
    out = correct_read(mem, "What breed is Rex?")
    assert out["verdict"] == "ABSTAIN"
    assert out["answer"] is None
    assert len(out["evidence"]) == 2                       # the conflict is SHOWN


def test_refuted_top_is_never_served(mem):
    a = mem.add("Rex is a labrador.", topic="pets", verified_by=["source-doc:alice:t1"])
    assert mem.semantic.set_epistemic(a["id"], make_refuted("vet-registry-42"))
    b = mem.add("Rex is a poodle.", topic="pets", verified_by=["source-doc:vet:t2"])
    out = correct_read(mem, "What breed is Rex?")
    assert out["verdict"] in ("CORRECT", "ACCEPT")
    assert "poodle" in out["answer"]
    assert a["id"] not in [out.get("served_id")]           # refuted never the answer


def test_abstain_when_store_silent(mem):
    out = correct_read(mem, "What is the capital of Mars?")
    assert out["verdict"] == "ABSTAIN"
    assert out["reason"] == "no_support"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
