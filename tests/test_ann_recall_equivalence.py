"""Wiring the ANN into recall must be BEHAVIOUR-PRESERVING: with the gate on,
recall returns the same top facts as the exact brute-force path.

The ANN pre-narrows the corpus to an oversampled candidate pool; the identical
filters/cosine/rerank then run inside the pool. On a corpus above the (lowered)
gate, ANN-on recall must match ANN-off recall on the top hits. Default OFF, so
the whole 5941-test suite is byte-identical until explicitly enabled.
"""
from __future__ import annotations

import pytest

pytest.importorskip("faiss")

from engram.semantic import Fact, SemanticMemory


def _seed(mem, n=140):
    # distinct, embeddable one-liners so recall has a clear ranking
    topics = ["python", "postgres", "redis", "docker", "kafka", "rust", "django"]
    for i in range(n):
        t = topics[i % len(topics)]
        mem.store(Fact(proposition=f"note {i}: the {t} service was configured "
                                   f"with setting number {i} today", topic="eq"),
                  embed="sync")


def test_ann_on_matches_bruteforce_on_top_hits(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", "0")   # isolate ANN from rerank
    mem = SemanticMemory(db_path=tmp_path / "semantic" / "semantic.db")
    _seed(mem, 140)
    q = "which service used redis configuration"

    monkeypatch.delenv("ENGRAM_ANN_RECALL", raising=False)
    off = mem.recall(q, k=8)

    # enable ANN with a gate low enough for a 140-fact corpus, fresh cache
    monkeypatch.setenv("ENGRAM_ANN_RECALL", "1")
    monkeypatch.setenv("ENGRAM_ANN_MIN_N", "50")
    mem._ann_cache.min_n = 50
    on = mem.recall(q, k=8)

    assert off, "brute-force returned nothing"
    assert mem._ann_cache.builds == 1, "ANN path was not exercised"
    # equivalence is on the SCORES (the ranking): identical top-k similarity
    # scores prove the ANN found the same facts. (Ties in score can reorder
    # the tied ids because numpy argsort is unstable and the pool has a
    # different input order — that's not a recall difference.)
    off_scores = [round(s, 5) for _, s in off]
    on_scores = [round(s, 5) for _, s in on]
    assert on_scores == off_scores
    # facts match except possibly the last slot, when a score tie at the
    # boundary lets the two paths keep different (equal-score) ids.
    assert len({f.id for f, _ in on} & {f.id for f, _ in off}) >= 7


def test_ann_default_off_is_byte_identical(tmp_path, monkeypatch):
    monkeypatch.delenv("ENGRAM_ANN_RECALL", raising=False)
    mem = SemanticMemory(db_path=tmp_path / "semantic" / "semantic.db")
    _seed(mem, 60)
    q = "docker service setting"
    # with the gate default-off, recall never touches the ANN path
    res = mem.recall(q, k=5)
    assert res and mem._ann_cache.builds == 0
