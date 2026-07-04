"""CYCLE #11 — regression test per token_usage_stats e recall_explain.

Senza questi metodi, mcp_server.py:4139 e :4377 cadevano nei rispettivi
fallback try/except AttributeError. I fallback erano graceful ma:
  - hippo_stats ritornava token totale = 0.0 anche su corpus reale
  - hippo_recall_explain ritornava breakdown ad-hoc duplicato in 2 punti

Questo test fissa il contratto pubblico: i metodi DEVONO esistere su
EpisodicMemory e produrre i dati attesi.
"""
from __future__ import annotations

import time

import pytest

from engram.memory import Episode, EpisodicMemory


@pytest.fixture
def memory(tmp_path):
    return EpisodicMemory(db_path=tmp_path / "ep.db")


def _store_ep(memory, eid: str, task: str, *, tokens: int = 0,
              outcome: str = "success", created_at: float | None = None) -> None:
    memory.store(Episode(
        id=eid, task_id=f"t-{eid}", task_text=task,
        final_answer="a", outcome=outcome, tokens_used=tokens,
        skills_used=[], traces=[],
        created_at=created_at if created_at is not None else time.time(),
    ))


# ---------- token_usage_stats -------------------------------------------


def test_token_usage_stats_method_exists(memory):
    assert hasattr(memory, "token_usage_stats")


def test_token_usage_stats_empty_db_zero(memory):
    r = memory.token_usage_stats()
    assert r["total"] == 0.0
    assert r["mean"] == 0.0
    assert r["max"] == 0.0
    assert r["n_with_tokens"] == 0.0


def test_token_usage_stats_aggregates_tokens(memory):
    _store_ep(memory, "e1", "task1", tokens=100)
    _store_ep(memory, "e2", "task2", tokens=200)
    _store_ep(memory, "e3", "task3", tokens=300)
    r = memory.token_usage_stats()
    assert r["total"] == 600.0
    assert r["mean"] == 200.0
    assert r["max"] == 300.0
    assert r["n_with_tokens"] == 3.0


def test_token_usage_stats_matches_summary(memory):
    """L'alias deve restituire IDENTICAMENTE token_usage_summary."""
    _store_ep(memory, "e1", "task1", tokens=50)
    a = memory.token_usage_stats()
    b = memory.token_usage_summary()
    assert a == b


# ---------- recall_explain ----------------------------------------------


def test_recall_explain_method_exists(memory):
    assert hasattr(memory, "recall_explain")


def test_recall_explain_empty_db_returns_empty(memory):
    out = memory.recall_explain("anything", k=5)
    assert out == []


def test_recall_explain_returns_breakdown_structure(memory):
    _store_ep(memory, "e1", "reverse string task")
    out = memory.recall_explain("reverse the string", k=5)
    assert len(out) >= 1
    h = out[0]
    assert "episode" in h
    assert "score" in h
    assert "breakdown" in h
    bk = h["breakdown"]
    for required in ("vector_similarity", "salience_boost",
                     "access_count_weight", "retention_strength",
                     "context_tcm"):
        assert required in bk, f"missing breakdown key: {required}"
    assert isinstance(bk["vector_similarity"], float)


def test_recall_explain_respects_k(memory):
    for i in range(10):
        _store_ep(memory, f"e{i}", f"task variant {i}", created_at=float(i))
    out = memory.recall_explain("task", k=3)
    assert len(out) <= 3
