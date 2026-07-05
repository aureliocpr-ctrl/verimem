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

    monkeypatch.setenv("ENGRAM_ANN_RECALL", "0")
    off = mem.recall(q, k=8)

    # enable ANN with a gate low enough for a 140-fact corpus, fresh cache.
    # Background contract (iter 26): the first enabled recall SPAWNS the build
    # and stays brute; once built, the pool serves.
    monkeypatch.setenv("ENGRAM_ANN_RECALL", "1")
    monkeypatch.setenv("ENGRAM_ANN_MIN_N", "50")
    mem._ann_cache.min_n = 50
    first = mem.recall(q, k=8)          # spawns background build, exact brute
    assert [f.id for f, _ in first] == [f.id for f, _ in off]
    import time as _t
    t0 = _t.time()
    while mem._ann_cache.building and _t.time() - t0 < 20:
        _t.sleep(0.05)
    on = mem.recall(q, k=8)             # index ready -> ANN pool serves

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


def test_ann_default_auto_dormant_below_gate(tmp_path, monkeypatch):
    """Post-flip default: AUTO-ON, but the _ANN_MIN_N gate keeps it fully
    dormant below 100k facts — small corpora never build or query an index."""
    monkeypatch.delenv("ENGRAM_ANN_RECALL", raising=False)
    monkeypatch.delenv("ENGRAM_ANN_MIN_N", raising=False)
    mem = SemanticMemory(db_path=tmp_path / "semantic" / "semantic.db")
    _seed(mem, 60)
    q = "docker service setting"
    res = mem.recall(q, k=5)
    assert res and mem._ann_cache.builds == 0
    assert not mem._ann_cache.building


def test_ann_env_zero_opts_out(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGRAM_ANN_RECALL", "0")
    monkeypatch.setenv("ENGRAM_ANN_MIN_N", "50")
    mem = SemanticMemory(db_path=tmp_path / "semantic" / "semantic.db")
    _seed(mem, 60)
    res = mem.recall("docker service setting", k=5)
    assert res and mem._ann_cache.builds == 0 and not mem._ann_cache.building
