"""Fase-C audit mod.3 — guardian.py line-by-line (2026-07-17). Three real
defects found by reading, pinned RED here before the fix:

1. MED — the tie-check compares FACTS, not VALUES (line ~105): with TWO proven
   facts agreeing on "labrador" vs one unlabeled "poodle", ``all(rank(best) >
   rank(other))`` fails against the agreeing twin → ABSTAIN instead of CORRECT.
   Perverse: MORE corroboration ⇒ MORE abstention. Dominance must be computed
   per-VALUE (the best value's rank strictly above every OTHER value's rank).
2. LOW — ``_rank`` does ``_RANK[label["kind"]]``: an unknown epistemic kind is
   a KeyError that crashes the read-path (line 109 defends with ``.get`` — the
   two must agree).
3. LOW — ``facts[0]`` IndexErrors when every re-fetch by id returns None
   (search hits present, store rows gone: delete race). A read-path must
   degrade to ABSTAIN, never crash.
"""
from __future__ import annotations

import pytest

from engram.epistemic import make_proven
from engram.guardian import _rank, correct_read


@pytest.fixture()
def mem(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGRAM_SOURCE_TRUST", "0")
    monkeypatch.setenv("ENGRAM_RECONCILE_ON_WRITE", "0")
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", "0")
    from engram.client import Memory
    return Memory(tmp_path / "g.db")


def test_corroborated_value_beats_lone_unlabeled_rival(mem):
    # same value twice ("labrador", different article so no dedup), both proven
    a = mem.add("Rex is a labrador.", topic="pets",
                verified_by=["source-doc:alice:t1"])
    b = mem.add("Rex is the labrador.", topic="pets",
                verified_by=["source-doc:vet:t2"])
    assert mem.semantic.set_epistemic(a["id"], make_proven("qa:kennel_check"))
    assert mem.semantic.set_epistemic(b["id"], make_proven("qa:vet_registry"))
    mem.add("Rex is a poodle.", topic="pets",
            verified_by=["source-doc:bob:t1"])          # lone, unlabeled
    out = correct_read(mem, "What breed is Rex?")
    # the corroborated proven VALUE dominates the unlabeled rival — this must
    # be a CORRECTION, not an abstention (per-fact tie-check bug)
    assert out["verdict"] == "CORRECT", out
    assert "labrador" in out["answer"]


def test_unknown_epistemic_kind_never_crashes():
    class _F:
        epistemic = {"kind": "certified_by_auditor"}    # future/foreign label

    assert _rank(_F()) == 0                              # unknown = unlabeled


def test_all_hits_unfetchable_abstains_not_crashes(mem, monkeypatch):
    mem.add("Rex is a labrador.", topic="pets",
            verified_by=["source-doc:alice:t1"])
    assert mem.search("Rex")                             # hits exist
    monkeypatch.setattr(type(mem.semantic), "get",
                        lambda self, fact_id: None)      # rows gone (race)
    out = correct_read(mem, "What breed is Rex?")
    assert out["verdict"] == "ABSTAIN"
    assert out["reason"] == "no_support"
