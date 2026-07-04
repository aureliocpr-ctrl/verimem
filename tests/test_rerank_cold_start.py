"""Recall must NOT pay the rerank budget on every query during the CE cold load.

Empirical motivation (2026-06-14 stress test, isolated DB, 50 recalls): recall
p50=236ms but p95=3.1s / max=3.5s — because while the cross-encoder is doing its
~33s cold load, EVERY query spawns the rerank worker and waits the full
``_recall_rerank_budget_s()`` (3s) before degrading to bi-encoder order. That 3s
tail is the "recall block" Aurelio keeps reporting.

Fix: a cold-start fast-path — if the CE isn't loaded yet, degrade INSTANTLY to the
(already valid) bi-encoder order and warm the model once in the background, so no
query pays the budget during the load window. Once warm, full reranking resumes.
"""
from __future__ import annotations

import time
import types

import engram.semantic as S
from engram.semantic import SemanticMemory


def _hits(n=5):
    # descending bi-encoder order; _rerank_stage2 uses f.id + f.proposition
    return [
        (types.SimpleNamespace(id=str(i), proposition=f"short prop {i}"), 0.9 - i * 0.01)
        for i in range(n)
    ]


def test_recall_degrades_fast_during_ce_cold_load(tmp_path, monkeypatch):
    """PRE-FIX this waits the full 3s budget; POST-FIX it is capped to the small
    cold budget (~0.25s) while the CE warms in the daemon worker."""
    monkeypatch.setattr(S, "_RERANKER", None, raising=False)  # CE not loaded
    monkeypatch.setattr(S, "_recall_rerank_budget_s", lambda: 3.0)
    monkeypatch.setattr(S, "_rerank_cold_budget_s", lambda: 0.25)

    # Simulate the slow cold load: any synchronous load blocks past the budget.
    def _slow_load():
        time.sleep(5.0)
        return lambda pairs: [0.5] * len(pairs)

    monkeypatch.setattr(S, "_load_reranker", _slow_load)

    sm = SemanticMemory(db_path=tmp_path / "s.db")
    hits = _hits(5)
    t0 = time.perf_counter()
    out = sm._rerank_stage2("query text", hits, 3)
    dt = time.perf_counter() - t0

    # The whole point: no per-query budget wait during the cold load.
    assert dt < 0.8, f"recall waited {dt:.2f}s during CE cold load (must degrade instantly)"
    # bi-encoder order preserved, capped at k
    assert [f.id for f, _ in out] == ["0", "1", "2"]


def test_rerank_still_runs_once_ce_is_loaded(tmp_path, monkeypatch):
    """When the CE IS loaded, the rerank actually reorders (no regression)."""
    monkeypatch.setattr(S, "_recall_rerank_budget_s", lambda: 3.0)
    # Pretend the model is already resident: _reranker_ready() must see it.
    monkeypatch.setattr(S, "_RERANKER", object(), raising=False)

    monkeypatch.setattr(S, "_load_reranker", lambda: (lambda pairs: [0.0] * len(pairs)))
    # Mock the primitive to REVERSE the order, proving the rerank path ran
    # rather than the bi-encoder fast-path (the empty test DB carries no props).
    import engram.cross_encoder_rerank as CER
    monkeypatch.setattr(
        CER, "rerank_candidates",
        lambda query, ids, **kw: [(fid, 0.0) for fid in reversed(list(ids))],
    )

    sm = SemanticMemory(db_path=tmp_path / "s.db")
    hits = _hits(4)
    out = sm._rerank_stage2("q", hits, 4)
    # rerank ran → order changed from bi-encoder ['0','1','2','3']
    assert [f.id for f, _ in out] != ["0", "1", "2", "3"]
    assert {f.id for f, _ in out} == {"0", "1", "2", "3"}  # no hit lost
