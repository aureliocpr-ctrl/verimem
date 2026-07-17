"""Audit 3-round R2 #13 (correctness): recall_hybrid must not re-bury the facts
the default-ON fusion was added to rescue.

recall() (fusion ON) adds graph/lexical-rescued facts to the pool with cos_sim
== 0.0 (they entered via PPR/BM25, not cosine). recall_hybrid then re-scores
every candidate as w*cos + (1-w)*kw_overlap, so a rescued fact with little
keyword overlap scores ~0 and is dropped — the exact multi-hop/exact-token case
the fusion exists to surface. Fix: a cos==0 candidate is scored with the pool's
MEDIAN positive cosine (recall_hybrid can't see the PPR/BM25 signal that saved
it), so it competes with the median dense hit instead of collapsing to 0.

Unit test: monkeypatch recall() to return controlled cosines, so the assertion
does not depend on fragile embedding values.
"""
from __future__ import annotations

import pytest

from verimem.semantic import Fact, SemanticMemory


def test_recall_hybrid_does_not_zero_fusion_rescued(tmp_path, monkeypatch):
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    gold = Fact(proposition="rescued multi-hop note", topic="t")       # fusion-rescued
    strong = Fact(proposition="strong dense hit", topic="t")
    weak = Fact(proposition="weak dense hit", topic="t")
    # fusion ON: the gold entered the pool via PPR/BM25 with cos_sim == 0.0.
    monkeypatch.setattr(
        sm, "recall",
        lambda q, **kw: [(strong, 0.9), (weak, 0.1), (gold, 0.0)])

    res = sm.recall_hybrid("anything", k=2)
    ids = {f.id for f, _ in res}
    # median positive cosine = 0.5, so the gold (w*0.5) beats the weak dense
    # (w*0.1) instead of being zeroed out and dropped.
    assert gold.id in ids, "il fused-rescued (cos 0) non deve essere ri-seppellito"
    assert weak.id not in ids, "il dense piu' debole cede lo slot al fused mediano"


def test_recall_hybrid_no_fused_is_unchanged(tmp_path, monkeypatch):
    """Senza fused (nessun cos==0) il ranking resta quello classico cos+kw."""
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    a = Fact(proposition="a", topic="t")
    b = Fact(proposition="b", topic="t")
    monkeypatch.setattr(sm, "recall", lambda q, **kw: [(a, 0.9), (b, 0.4)])
    res = sm.recall_hybrid("anything", k=1)
    assert [f.id for f, _ in res] == [a.id], "top-1 resta il cosine piu' alto"
