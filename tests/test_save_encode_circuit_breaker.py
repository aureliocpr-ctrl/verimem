"""The save path must NEVER block the caller on a slow embedding.

Real bug (2026-06-06, Aurelio hit a ~40-min save hang): the encode daemon was
ALIVE but starved/unresponsive under heavy concurrent load (3 large Docker
builds), and store(embed="auto") fell through to a slow/blocking encode. The
4efb62d fix only bounded the model-LOCK wait, not the encode itself.

Fix: _encode_within_budget bounds the embed; on overrun it DEFERS (returns None
-> empty-embedding sentinel, keyword-findable, backfilled later) instead of
hanging. And embed="auto" now fails toward DEFER (not sync cold-load) on error.
"""
from __future__ import annotations

import time

import pytest

import verimem.semantic as sem


def test_encode_within_budget_defers_on_slow_encode(monkeypatch):
    # A pathologically slow encode must be abandoned at the budget, not awaited.
    def _slow(*_a, **_k):
        time.sleep(10)
        return [0.0] * 768

    monkeypatch.setattr(sem.embedding, "encode", _slow)
    monkeypatch.setattr(sem.embedding, "as_passage", lambda s: s)

    t0 = time.time()
    result = sem._encode_within_budget("x", budget_s=0.4)
    elapsed = time.time() - t0

    assert result is None, "slow encode must DEFER (return None), not block"
    assert elapsed < 3.0, f"circuit-breaker hung {elapsed:.1f}s (budget was 0.4s)"


def test_encode_within_budget_returns_vector_when_fast(monkeypatch):
    monkeypatch.setattr(sem.embedding, "encode", lambda *_a, **_k: [1.0] * 768)
    monkeypatch.setattr(sem.embedding, "as_passage", lambda s: s)
    result = sem._encode_within_budget("x", budget_s=5)
    assert result is not None and len(result) == 768


def test_encode_within_budget_propagates_real_error(monkeypatch):
    # A genuine encode FAILURE (not mere slowness) still surfaces to the caller.
    def _boom(*_a, **_k):
        raise RuntimeError("model broke")

    monkeypatch.setattr(sem.embedding, "encode", _boom)
    monkeypatch.setattr(sem.embedding, "as_passage", lambda s: s)
    with pytest.raises(RuntimeError, match="model broke"):
        sem._encode_within_budget("x", budget_s=5)


def test_store_auto_defers_under_slow_encode_no_hang(monkeypatch, tmp_path):
    """End-to-end WIRING: store(embed='auto') must DEFER (not hang) when the
    daemon LOOKS usable (answers the warmth ping) but the encode is
    pathologically slow — the exact alive-but-starved daemon Aurelio hit."""
    from verimem import encode_service as es
    from verimem.semantic import Fact, SemanticMemory

    monkeypatch.setattr(es, "daemon_usable", lambda: True)  # warm -> budgeted sync
    monkeypatch.setattr(sem, "_SAVE_ENCODE_BUDGET_S", 0.4)

    def _slow(*_a, **_k):
        time.sleep(10)
        return [0.0] * 768

    monkeypatch.setattr(sem.embedding, "encode", _slow)
    monkeypatch.setattr(sem.embedding, "as_passage", lambda s: s)

    sm = SemanticMemory(db_path=tmp_path / "sem.db")
    fact = Fact(proposition="hang-safety integration", topic="t",
                confidence=0.8, source_episodes=[], created_at=time.time())

    t0 = time.time()
    sm.store(fact, embed="auto")
    elapsed = time.time() - t0

    assert elapsed < 3.0, f"store(embed='auto') hung {elapsed:.1f}s — wiring broken"
    # the fact persisted (keyword-findable) despite the deferred embedding
    props = [f.proposition for f in sm.list_facts()]
    assert "hang-safety integration" in props
