"""Deterministic recall tie-break (iter 23, mandate: default flips authorized).

Before: the hot cached recall path picked top-k via ``np.argsort(-sims)`` —
tie order among EQUAL scores was quicksort-arbitrary and, on the ANN path,
depended on the faiss pool order. That made ANN-on recall score-identical but
not byte-identical, blocking the auto-enable default.

Now: top-k is selected by ``(-score, fact.id)`` (``_topk_deterministic``) —
identical output for ANY row ordering of the same candidate set. This is the
enabling property for ANN == brute EXACT equality.
"""
from __future__ import annotations

import numpy as np
import pytest

from engram.semantic import Fact, SemanticMemory, _topk_deterministic


class _F:
    def __init__(self, fid):
        self.id = fid


def test_topk_orders_ties_by_fact_id() -> None:
    sims = np.array([0.9, 0.9, 0.9, 0.5], dtype=np.float32)
    facts = [_F("c"), _F("a"), _F("b"), _F("z")]
    idx = _topk_deterministic(sims, 3, facts)
    assert [facts[i].id for i in idx] == ["a", "b", "c"]  # ties -> id order


def test_topk_boundary_tie_group_resolved_by_id() -> None:
    # boundary at n=2 falls INSIDE the 0.7 tie group: the id decides who's in
    sims = np.array([0.9, 0.7, 0.7, 0.7, 0.1], dtype=np.float32)
    facts = [_F("q"), _F("m"), _F("a"), _F("z"), _F("x")]
    idx = _topk_deterministic(sims, 2, facts)
    assert [facts[i].id for i in idx] == ["q", "a"]  # 'a' < 'm' < 'z'


def test_topk_row_order_invariance() -> None:
    """THE property: any permutation of the same candidate rows yields the
    same fact-id sequence — exactly what ANN pool narrowing needs."""
    rng = np.random.default_rng(3)
    sims = rng.choice([0.9, 0.8, 0.7], size=20).astype(np.float32)
    facts = [_F(f"f{i:02d}") for i in range(20)]
    base = None
    for seed in (0, 1, 2):
        perm = np.random.default_rng(seed).permutation(20)
        ids = [facts[perm[i]].id
               for i in _topk_deterministic(sims[perm], 7, [facts[j] for j in perm])]
        if base is None:
            base = ids
        assert ids == base


def test_topk_handles_neginf_and_small_n() -> None:
    sims = np.array([-np.inf, 0.5], dtype=np.float32)
    facts = [_F("a"), _F("b")]
    assert [facts[i].id for i in _topk_deterministic(sims, 5, facts)] == ["b", "a"]
    assert _topk_deterministic(np.array([], dtype=np.float32), 3, []).size == 0


def test_recall_ties_ordered_by_id_end_to_end(tmp_path) -> None:
    """Identical propositions -> identical embeddings -> exact score ties: the
    live recall must order them by fact id, deterministically."""
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    for fid in ("m2", "m0", "m1"):
        sm.store(Fact(id=fid, proposition="the port of the api server is 8080",
                      topic="t"), embed="sync")
    hits = sm.recall("api server port", k=3)
    tied = [f.id for f, s in hits]
    assert tied == sorted(tied), f"ties must be id-ordered, got {tied}"


@pytest.mark.skipif(pytest.importorskip("faiss") is None, reason="faiss")
def test_ann_on_equals_brute_exactly(tmp_path, monkeypatch) -> None:
    """With the deterministic tie-break, ANN-on recall returns the IDENTICAL
    fact-id sequence as brute-force — byte-identical, not just score-identical."""
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", "0")
    mem = SemanticMemory(db_path=tmp_path / "semantic" / "semantic.db")
    topics = ["python", "postgres", "redis", "docker", "kafka", "rust", "django"]
    for i in range(140):
        t = topics[i % len(topics)]
        mem.store(Fact(proposition=f"note {i}: the {t} service was configured "
                                   f"with setting number {i} today", topic="eq"),
                  embed="sync")
    q = "which service used redis configuration"
    monkeypatch.delenv("ENGRAM_ANN_RECALL", raising=False)
    off = mem.recall(q, k=8)
    monkeypatch.setenv("ENGRAM_ANN_RECALL", "1")
    monkeypatch.setenv("ENGRAM_ANN_MIN_N", "50")
    mem._ann_cache.min_n = 50
    on = mem.recall(q, k=8)
    assert mem._ann_cache.builds == 1, "ANN path not exercised"
    assert [f.id for f, _ in on] == [f.id for f, _ in off]
    assert [round(s, 6) for _, s in on] == [round(s, 6) for _, s in off]
