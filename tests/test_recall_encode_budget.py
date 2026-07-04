"""Recall must NEVER block on a slow/cold encode daemon.

Aurelio's reported symptom: "durante i recall ti blocchi". Unlike save (which
can DEFER to an empty-embedding sentinel), recall MUST encode the query — and
the legacy path had no budget, so a cold/contended daemon → in-process model
cold-load under _MODEL_LOCK → recall blocks for up to ~90s.

Fix: the recall query-encode is bounded; on overrun it falls back to KEYWORD
recall (SQL LIKE on proposition) — instant, still useful results — instead of
blocking. The warm-daemon path is unchanged (q_emb is computed normally and
flows into the existing cosine ranking).
"""
from __future__ import annotations

import time

import numpy as np
import pytest

import engram.semantic as sem
from engram.config import CONFIG
from engram.semantic import Fact, SemanticMemory


def _seed(sm):
    # Seed with a fast monkeypatched encode so the row has a (valid-shape) vector;
    # the keyword fallback path doesn't use it, but store() requires an encode.
    sm.store(Fact(proposition="the capital of France is Paris", topic="geo",
                  confidence=0.9, source_episodes=[], created_at=time.time()),
             embed="sync")
    sm.store(Fact(proposition="the capital of Spain is Madrid", topic="geo",
                  confidence=0.9, source_episodes=[], created_at=time.time()),
             embed="sync")


def test_recall_keyword_fallback_when_encode_times_out(monkeypatch, tmp_path):
    monkeypatch.setattr(sem.embedding, "encode",
                        lambda *_a, **_k: np.ones(CONFIG.embedding_dim, dtype=np.float32))
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    _seed(sm)

    # Now make the encode pathologically slow + a tiny recall budget.
    monkeypatch.setattr(sem, "_RECALL_ENCODE_BUDGET_S", 0.4)

    def _slow(*_a, **_k):
        time.sleep(10)
        return np.ones(CONFIG.embedding_dim, dtype=np.float32)

    monkeypatch.setattr(sem.embedding, "encode", _slow)

    t0 = time.time()
    hits = sm.recall("capital", k=5)
    elapsed = time.time() - t0

    assert elapsed < 3.0, f"recall hung {elapsed:.1f}s — keyword fallback failed"
    assert hits, "keyword fallback must return the matching facts, not []"
    props = [h[0].proposition for h in hits]
    assert any("capital" in p for p in props), f"expected keyword hits, got {props}"


def test_default_encode_budget_beats_proven_timeout_lower_bound():
    """Regression guard (2026-06-13): the DEFAULT recall query-encode budget must
    keep the COLD-path latency (budget + keyword search, no rerank) below the
    PROVEN lower bound of the MCP client request timeout. Live evidence: a full
    WARM recall (~3s, incl. the 3s rerank) succeeded post-restart, so the client
    timeout is >= ~3s. cold latency = budget + keyword(<0.5s); for that to be
    < 3s the budget must be <= ~2s. (Adversarial review rejected 4s as unproven:
    it only beats a timeout > 4s, which evidence doesn't establish.) Keep <= 2s."""
    assert sem._RECALL_ENCODE_BUDGET_S <= 2.0, (
        f"default recall encode budget {sem._RECALL_ENCODE_BUDGET_S}s + keyword "
        "may exceed the proven >=3s client timeout; first cold query times out"
    )


def test_recall_warm_path_unchanged_returns_cosine_tuples(monkeypatch, tmp_path):
    # Fast encode (warm) → recall takes the normal cosine path, returns (Fact, score).
    monkeypatch.setattr(sem.embedding, "encode",
                        lambda *_a, **_k: np.ones(CONFIG.embedding_dim, dtype=np.float32))
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    _seed(sm)
    hits = sm.recall("capital", k=5)
    assert hits, "warm recall must return results"
    for h in hits:
        assert isinstance(h, tuple) and len(h) == 2
        assert hasattr(h[0], "proposition") and isinstance(h[1], float)
