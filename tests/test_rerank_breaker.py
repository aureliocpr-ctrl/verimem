"""Rerank circuit-breaker (task #16) — TDD.

Observed live 2026-07-10 (external read-path runs): on a loaded CPU the CE
predict exceeds the 3s budget on EVERY query — each recall pays the full
budget in wasted wall-clock and keeps bi-encoder order anyway. The breaker
turns systematic overruns into a one-time decision: after N consecutive
overruns the CE is disabled for the session (explicit log), recall stops
waiting. A successful rerank resets the count (transient contention must not
permanently disable the measured R@1 lift).

All tests inject a fake scorer — no model, no RAM.
"""
from __future__ import annotations

import time

import pytest

from engram import semantic
from engram.client import Memory

FACTS = [
    "The Eiffel Tower is a wrought-iron lattice tower in Paris.",
    "Marie Curie won two Nobel Prizes for her work on radioactivity.",
    "The Amazon River discharges more water than any other river.",
]


@pytest.fixture(autouse=True)
def _fresh_breaker():
    semantic._rerank_breaker_reset()
    yield
    semantic._rerank_breaker_reset()


def _mem(tmp_path, monkeypatch, *, scorer_delay: float, budget: str = "0.2"):
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", "1")
    monkeypatch.setenv("HIPPO_RECALL_RERANK_BUDGET_S", budget)
    monkeypatch.setenv("ENGRAM_RERANK_COLD_BUDGET_S", budget)
    monkeypatch.setenv("ENGRAM_RERANK_BREAKER_N", "3")

    def slow_scorer():
        def score(pairs):
            time.sleep(scorer_delay)
            return [0.5] * len(pairs)
        return score

    monkeypatch.setattr(semantic, "_load_reranker", slow_scorer)
    # the ready-check gates the cold budget; pretend the CE is resident so
    # the configured budget applies deterministically
    monkeypatch.setattr(semantic, "_reranker_ready", lambda: True)
    mem = Memory(tmp_path / "m.db")
    for f in FACTS:
        mem.add(f, topic="brk", verified_by=["source-doc:t"])
    return mem


def test_breaker_trips_after_consecutive_overruns(tmp_path, monkeypatch):
    mem = _mem(tmp_path, monkeypatch, scorer_delay=1.0)  # >> 0.2s budget
    for _ in range(3):
        mem.search("where is the tower", k=3)
    assert semantic._RERANK_BREAKER["tripped"] is True
    t0 = time.time()
    mem.search("where is the tower", k=3)
    assert time.time() - t0 < 0.15, (
        "tripped breaker must skip the rerank wait entirely")


def test_success_resets_consecutive_count(tmp_path, monkeypatch):
    mem = _mem(tmp_path, monkeypatch, scorer_delay=1.0)
    for _ in range(2):
        mem.search("tower", k=3)  # 2 overruns
    assert semantic._RERANK_BREAKER["consecutive"] == 2
    # a fast scorer now succeeds within budget → count resets
    monkeypatch.setattr(
        semantic, "_load_reranker",
        lambda: (lambda pairs: [0.5] * len(pairs)))
    mem.search("tower", k=3)
    assert semantic._RERANK_BREAKER["consecutive"] == 0
    assert semantic._RERANK_BREAKER["tripped"] is False


def test_breaker_disabled_with_zero_threshold(tmp_path, monkeypatch):
    mem = _mem(tmp_path, monkeypatch, scorer_delay=1.0)
    monkeypatch.setenv("ENGRAM_RERANK_BREAKER_N", "0")
    for _ in range(5):
        mem.search("tower", k=3)
    assert semantic._RERANK_BREAKER["tripped"] is False


# --- F1 C1 (task #25): cold-load overruns must NOT trip the steady breaker.
# Observed on the MuSiQue virgin-corpus run 2026-07-10: the CE cold-load
# (~33s) overran the 0.25s cold budget 5 times in the first recalls of a
# fresh process and TRIPPED the breaker — rerank (worth +0.29 R@1) stayed
# off for the whole session. A cold overrun is transient by definition; only
# a STEADY overrun (CE resident but too slow) signals a real problem.


def test_cold_overruns_do_not_trip_steady_breaker(tmp_path, monkeypatch):
    mem = _mem(tmp_path, monkeypatch, scorer_delay=1.0)
    monkeypatch.setattr(semantic, "_reranker_ready", lambda: False)  # cold
    for _ in range(5):  # >> breaker N=3
        mem.search("tower", k=3)
    assert semantic._RERANK_BREAKER["tripped"] is False, (
        "cold-load overruns are transient — they must never trip the breaker")
    assert semantic._RERANK_BREAKER["consecutive"] == 0, (
        "cold overruns must not count toward the steady trip")


def test_cold_overruns_have_their_own_bounded_trip(tmp_path, monkeypatch):
    # pathological never-warms process (broken CE install): a SEPARATE,
    # much more generous cold threshold still bounds the waste.
    mem = _mem(tmp_path, monkeypatch, scorer_delay=1.0)
    monkeypatch.setattr(semantic, "_reranker_ready", lambda: False)
    monkeypatch.setenv("ENGRAM_RERANK_COLD_BREAKER_N", "3")
    for _ in range(3):
        mem.search("tower", k=3)
    assert semantic._RERANK_BREAKER["tripped"] is True


def test_steady_overruns_still_trip_after_warm(tmp_path, monkeypatch):
    # regression guard: the C1 fix must not weaken the original breaker —
    # a WARM reranker that systematically overruns still trips at N.
    mem = _mem(tmp_path, monkeypatch, scorer_delay=1.0)  # ready=True fixture
    for _ in range(3):
        mem.search("tower", k=3)
    assert semantic._RERANK_BREAKER["tripped"] is True
