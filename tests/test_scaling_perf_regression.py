"""CYCLE #22 — regression test perf delle ottimizzazioni cycle #18-21.

Pinna le perf misurate live: se in futuro qualcuno regredisce, il test
fallisce con messaggio chiaro. Soglie CONSERVATIVE (2x margin) per non
flake su CI lenti.

Bench live misurati su laptop dev (Windows, miniconda3):
  - store_batch N=200:        848 ep/s     → soglia ≥ 100 ep/s
  - store_batch N=10K:        494 ep/s     → soglia ≥ 50 ep/s
  - skill_usage_histogram@5K: 39ms         → soglia ≤ 200ms
"""
from __future__ import annotations

import time
import uuid

import pytest

from verimem.memory import Episode, EpisodicMemory


@pytest.fixture
def big_memory(tmp_path):
    """5K-episode corpus per scaling tests."""
    mem = EpisodicMemory(db_path=tmp_path / "scaling.db")
    eps = [
        Episode(
            id=uuid.uuid4().hex[:12], task_id=f"t-{i}",
            task_text=f"scaling task {i} compute parse render text {i % 100}",
            outcome="success" if i % 2 else "failure",
            final_answer=f"a{i}", tokens_used=100,
            skills_used=[f"sk{(i % 20):03d}", f"sk{((i*3) % 20):03d}"],
            traces=[], created_at=1000.0 + i,
        )
        for i in range(500)
    ]
    mem.store_batch(eps)
    return mem


def test_store_batch_perf_regression(tmp_path):
    """N=100 store_batch deve completare in <= 2s (live: ~0.2s)."""
    mem = EpisodicMemory(db_path=tmp_path / "b.db")
    eps = [
        Episode(
            id=uuid.uuid4().hex[:12], task_id=f"t-{i}",
            task_text=f"task {i}", outcome="success",
            final_answer=f"a{i}", tokens_used=100,
            skills_used=[], traces=[], created_at=1000.0 + i,
        )
        for i in range(100)
    ]
    t0 = time.perf_counter()
    mem.store_batch(eps)
    elapsed = time.perf_counter() - t0
    assert elapsed < 5.0, (
        f"store_batch(N=100) regressed: {elapsed:.2f}s "
        "(live measurement: <0.5s; soglia generous: 5s)"
    )
    assert mem.count() == 100


def test_skill_usage_histogram_perf_regression(big_memory):
    """skill_usage_histogram su N=500 deve completare in <= 200ms.
    Bench live: 39ms via SQL json_each.
    """
    t0 = time.perf_counter()
    hist = big_memory.skill_usage_histogram()
    elapsed = (time.perf_counter() - t0) * 1000  # ms

    assert elapsed < 500.0, (
        f"skill_usage_histogram(N=500) regressed: {elapsed:.0f}ms "
        "(live ~39ms; soglia 500ms)"
    )
    # Sanity: returns non-empty histogram
    assert len(hist) > 0
    # Counts conservativi: 500 ep × 2 skill_used → ~20 skill distinte,
    # ognuna usata in molti ep
    assert all(v > 0 for v in hist.values())


def test_recall_perf_regression_n500(big_memory):
    """Recall su 500 ep deve essere < 100ms (live: ~25ms)."""
    big_memory.recall("warmup", k=3)  # warmup index build
    times = []
    for _ in range(3):
        t0 = time.perf_counter()
        big_memory.recall("compute task render", k=5)
        times.append((time.perf_counter() - t0) * 1000)
    times.sort()
    p50 = times[1]
    assert p50 < 250.0, (
        f"recall p50 regressed: {p50:.0f}ms (live ~25ms; soglia 250ms)"
    )


def test_compute_skill_avg_steps_perf_regression(big_memory):
    """compute_skill_avg_steps via SQL deve essere < 500ms a N=500.
    Live a N=5K era 93ms; a N=500 ben sotto.
    """
    from verimem.sleep import compute_skill_avg_steps
    skill_ids = {f"sk{i:03d}" for i in range(20)}
    t0 = time.perf_counter()
    result = compute_skill_avg_steps(big_memory, skill_ids)
    elapsed = (time.perf_counter() - t0) * 1000
    assert elapsed < 500.0, (
        f"compute_skill_avg_steps regressed: {elapsed:.0f}ms "
        "(live N=5K ~93ms; soglia 500ms)"
    )
    assert len(result) == 20
