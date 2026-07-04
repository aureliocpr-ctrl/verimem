"""RRF fusion of dense cosine + PPR ranklists (competitor-gap step 2b core).

Pure function: dense (Fact, sim) hits fused with a PPR fact-id ranklist; PPR-only
facts (reached via shared entities even at cosine ~0) enter the pool with sim=0 so
the downstream CE-rerank can rescue them. Fail-soft. No SemanticMemory dependency.
"""
from __future__ import annotations

import types

from engram.ppr_seed import fuse_dense_and_ppr


def _F(fid):
    return types.SimpleNamespace(id=fid, proposition=f"prop-{fid}")


def test_ppr_only_fact_enters_pool_with_sim_zero():
    dense = [(_F("A"), 0.9), (_F("B"), 0.5)]
    ppr_ids = ["C", "A"]  # C is PPR-only (cosine missed it); A overlaps
    store = {"C": _F("C")}
    out = fuse_dense_and_ppr(dense, [ppr_ids], lambda i: store.get(i))
    by = {f.id: s for f, s in out}
    assert set(by) == {"A", "B", "C"}, "the PPR-only fact must be added to the pool"
    assert by["C"] == 0.0, "a PPR-only fact enters with sim 0 for the CE-rerank to score"
    assert by["A"] == 0.9, "a dense fact keeps its cosine sim"


def test_empty_ppr_returns_dense_unchanged():
    dense = [(_F("A"), 0.9), (_F("B"), 0.5)]
    assert fuse_dense_and_ppr(dense, [], lambda i: None) == dense


def test_failsoft_on_fetch_error_skips_that_id():
    dense = [(_F("A"), 0.9)]

    def boom(_i):
        raise RuntimeError("db down")

    out = fuse_dense_and_ppr(dense, [["Z"]], boom)  # Z fetch raises -> skipped
    assert [f.id for f, _ in out] == ["A"], "a failing fetch must not break recall"


def test_rrf_orders_shared_top_fact_first():
    # A is rank-1 in BOTH dense and ppr -> highest summed RRF score -> first
    dense = [(_F("A"), 0.9), (_F("B"), 0.8)]
    ppr_ids = ["A", "C"]
    out = fuse_dense_and_ppr(dense, [ppr_ids], _F)
    assert out[0][0].id == "A"
    assert {f.id for f, _ in out} == {"A", "B", "C"}


def test_missing_ppr_fact_not_in_store_is_dropped():
    dense = [(_F("A"), 0.9)]
    out = fuse_dense_and_ppr(dense, [["GHOST"]], lambda i: None)  # fetch returns None
    assert [f.id for f, _ in out] == ["A"], "an unfetchable PPR id is silently dropped"
