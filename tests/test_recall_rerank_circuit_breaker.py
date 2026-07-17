"""Circuit-breaker on the stage-2 CE rerank (2026-06-13, Aurelio hit it live).

Measured root cause: `_load_reranker` COLD = ~33s (CrossEncoder first
load), steady predict ~1.7s. Under CPU contention the cold-load was the
10-minute recall hang Aurelio saw (recall MCP killed with ESC). The
stage-2 try/except catches scorer EXCEPTIONS but NOT a hang — a slow
load/predict just blocks.

Fix: run load+score in a daemon thread joined with a wall-clock budget
(mirror of `_encode_prepared_within_budget`). On overrun return the
already-valid bi-encoder order and let the model finish warming in the
background, so the NEXT query reranks. Worst case 10min -> ~budget.

RED marker: pre-fix a 5s scorer makes recall take ~5s; the budget caps it.
"""
from __future__ import annotations

import time

from verimem.semantic import Fact, SemanticMemory

_QUERY = "blue-green deployment on aws"


def _seed(sm: SemanticMemory) -> None:
    props = [
        "the deployment uses blue-green rollout on aws",
        "carbonara needs guanciale eggs pecorino black pepper",
        "sqlite backup integrity is verified with pragma integrity_check",
        "the recall path ranks facts by cosine over embeddings",
        "skills are consolidated during the dream rem stage",
    ]
    for i, p in enumerate(props):
        sm.store(Fact(proposition=p, topic=f"t/{i}", source_episodes=["e"]),
                 embed="sync")


def _ids(res: list[tuple]) -> list[str]:
    return [f.id for f, _ in res]


def _reversing_loader():
    """Fast scorer that reverses order (rerank visibly applied)."""
    return lambda pairs: [float(i) for i in range(len(pairs))]


def _slow_scorer_loader(delay_s: float):
    def _load():
        def _score(pairs):
            time.sleep(delay_s)
            return [float(i) for i in range(len(pairs))]
        return _score
    return _load


def _slow_load_loader(delay_s: float):
    """Simulate the ~33s COLD load: the loader itself blocks."""
    def _load():
        time.sleep(delay_s)
        return lambda pairs: [float(i) for i in range(len(pairs))]
    return _load


# ── overrun → bi-encoder fallback, bounded latency ──────────────────────────

def test_slow_scorer_falls_back_within_budget(tmp_path, monkeypatch):
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    _seed(sm)
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", "0")
    base_ids = _ids(sm.recall(_QUERY, k=5))

    monkeypatch.setattr("verimem.semantic._load_reranker",
                        _slow_scorer_loader(5.0), raising=False)
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", "1")
    monkeypatch.setenv("HIPPO_RECALL_RERANK_BUDGET_S", "0.3")

    t0 = time.perf_counter()
    res = sm.recall(_QUERY, k=5)
    elapsed = time.perf_counter() - t0

    assert elapsed < 2.0, f"recall hung {elapsed:.1f}s on a 5s scorer (budget 0.3)"
    assert _ids(res) == base_ids, "overrun must preserve bi-encoder order"


def test_slow_cold_load_falls_back_within_budget(tmp_path, monkeypatch):
    """The 33s symptom: the LOADER itself blocks (cold CrossEncoder)."""
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    _seed(sm)
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", "0")
    base_ids = _ids(sm.recall(_QUERY, k=5))

    monkeypatch.setattr("verimem.semantic._load_reranker",
                        _slow_load_loader(5.0), raising=False)
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", "1")
    monkeypatch.setenv("HIPPO_RECALL_RERANK_BUDGET_S", "0.3")

    t0 = time.perf_counter()
    res = sm.recall(_QUERY, k=5)
    elapsed = time.perf_counter() - t0

    assert elapsed < 2.0, f"recall hung {elapsed:.1f}s on a 5s cold-load"
    assert _ids(res) == base_ids


# ── within budget → rerank still applies ────────────────────────────────────

def test_fast_reranker_still_applies(tmp_path, monkeypatch):
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    _seed(sm)
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", "0")
    base_ids = _ids(sm.recall(_QUERY, k=5))

    monkeypatch.setattr("verimem.semantic._load_reranker", _reversing_loader,
                        raising=False)
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", "1")
    monkeypatch.setenv("HIPPO_RECALL_RERANK_BUDGET_S", "5")
    res = sm.recall(_QUERY, k=5)
    assert _ids(res) == list(reversed(base_ids)), (
        "a fast scorer within budget must still reorder"
    )


def test_budget_env_configurable(tmp_path, monkeypatch):
    """A generous budget lets a slow-but-finishing scorer complete."""
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    _seed(sm)
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", "0")
    base_ids = _ids(sm.recall(_QUERY, k=5))

    monkeypatch.setattr("verimem.semantic._load_reranker",
                        _slow_scorer_loader(0.5), raising=False)
    # CE resident → the FULL budget applies (the 2026-06-14 cold-budget cap only
    # guards the first query during the ~33s cold load, exercised separately in
    # test_rerank_cold_start). This test is about the steady, warm-CE budget.
    monkeypatch.setattr("verimem.semantic._RERANKER", object(), raising=False)
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", "1")
    monkeypatch.setenv("HIPPO_RECALL_RERANK_BUDGET_S", "3")
    res = sm.recall(_QUERY, k=5)
    assert _ids(res) == list(reversed(base_ids)), (
        "budget 3s must let a 0.5s scorer finish and reorder"
    )
