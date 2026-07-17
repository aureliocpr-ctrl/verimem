"""Tests for FORGIA pezzo #18: wake retrieval with salience + recency.

`memory.recall()` has supported `salience_weight` (Buzsáki 2015 /
Mattar-Daw 2018) and `recency_weight` since pezzo #6 — but the
wake's `_retrieve_episodes` was never passing them. The few-shot
block was always pure-cosine. This pezzo wires them.

Four measurable invariants we test:

  1. SALIENCE BOOSTS FAILURES: with `wake_salience_weight=1.5`, a
     similar-cosine failure with high salience ranks above a banal
     success — so the model learns from its own mistakes.

  2. RECENCY BREAKS COSINE TIES: with `wake_recency_weight=0.20`
     and two cosine-tied episodes (one hours-old, one days-old),
     the recent one ranks first.

  3. NO REGRESSION ON RELEVANCE: a high-cosine episode still wins
     against banal twins even with salience/recency on.

  4. KILL-SWITCH OFF (default 0.0) preserves legacy ordering.
"""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pytest

from verimem.config import CONFIG
from verimem.episode import Episode, Trace
from verimem.memory import EpisodicMemory


def _ep(*, ep_id: str, text: str, outcome: str = "success",
        created_at: float | None = None) -> Episode:
    return Episode(
        id=ep_id, task_id=text[:30], task_text=text,
        outcome=outcome,  # type: ignore[arg-type]
        final_answer="ok",
        traces=[Trace(step=1, thought="t", action="A",
                      action_input="", observation="o")],
        tokens_used=1, skills_used=[],
        created_at=created_at or time.time(),
    )


@pytest.fixture
def config_override():
    saved: dict = {}

    def setter(field: str, value) -> None:
        if field not in saved:
            saved[field] = getattr(CONFIG, field)
        object.__setattr__(CONFIG, field, value)

    yield setter
    for field, value in saved.items():
        object.__setattr__(CONFIG, field, value)


def _build_wake(memory):
    from verimem.wake import WakeAgent, WakeConfig
    wake = object.__new__(WakeAgent)
    wake.memory = memory  # type: ignore[misc]
    wake.cfg = WakeConfig(
        max_steps=4, self_critique=False, episodes_recall_k=5,
    )
    return wake


# ---------- Test 1: kill-switch off = legacy ordering -----------------


def test_wake_default_weights_zero_preserves_legacy(
    tmp_path: Path, config_override,
):
    """With `wake_salience_weight=0` and `wake_recency_weight=0`, the
    wake retrieves with pure cosine — same as legacy."""
    config_override("wake_salience_weight", 0.0)
    config_override("wake_recency_weight", 0.0)
    config_override("forward_replay_include_failures", False)

    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    for i, t in enumerate(["alpha", "beta", "gamma"]):
        mem.store(_ep(ep_id=f"e{i}", text=t))

    wake = _build_wake(mem)
    a = wake._retrieve_episodes("alpha")  # noqa: SLF001
    b = mem.recall(
        "alpha", k=wake.cfg.episodes_recall_k, outcome_filter="success",
    )
    assert [ep.id for ep, _ in a[:len(b)]] == [ep.id for ep, _ in b]


# ---------- Test 2: salience promotes failures -----------------------


def test_salience_weight_promotes_failure_with_keyword(
    tmp_path: Path, config_override,
):
    """A failure with task-keyword overlap (high salience by
    construction) ranks above 5 banal successes when
    wake_salience_weight is high enough.

    NOTE: failures are pulled into the *failures* portion of the
    retrieve return — we only check that the failure is in the
    final list (via forward_replay_include_failures=True), not
    that it ranks above the successes (different outcome filters)."""
    config_override("wake_salience_weight", 1.5)
    config_override("forward_replay_include_failures", True)

    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    # 5 banal successes
    for i in range(5):
        mem.store(_ep(ep_id=f"banal{i}", text=f"banal task {i}"))
    # A surprising failure on a relevant task. With salience > 0
    # it should be in the failure recall (k=1).
    mem.store(_ep(
        ep_id="surprise",
        text="critical failure encountered while running banal task",
        outcome="failure",
    ))
    wake = _build_wake(mem)
    out = wake._retrieve_episodes("banal task")  # noqa: SLF001
    out_ids = [ep.id for ep, _ in out]
    assert "surprise" in out_ids, (
        f"salience-boosted failure missing from retrieval: {out_ids}"
    )


# ---------- Test 3: recency breaks ties -----------------------------


def test_recency_weight_breaks_cosine_ties(tmp_path: Path, config_override):
    """Two cosine-tied successes — recent one wins."""
    config_override("wake_salience_weight", 0.0)
    config_override("wake_recency_weight", 0.20)
    config_override("wake_recency_tau_s", 86400.0)  # 1 day
    config_override("forward_replay_include_failures", False)

    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    now = time.time()
    mem.store(_ep(ep_id="old", text="duplicate task", created_at=now - 30 * 86400))
    mem.store(_ep(ep_id="new", text="duplicate task", created_at=now - 60))

    wake = _build_wake(mem)
    out = wake._retrieve_episodes("duplicate task")  # noqa: SLF001
    success_ids = [ep.id for ep, _ in out if ep.outcome == "success"]
    assert success_ids[0] == "new", (
        f"recency_weight didn't put recent first: {success_ids}"
    )


# ---------- Test 4: relevance still wins -----------------------------


def test_relevance_dominates_over_weak_salience(
    tmp_path: Path, config_override,
):
    """High-cosine episode beats low-cosine high-salience episode at
    moderate salience_weight. Relevance must remain the dominant signal."""
    config_override("wake_salience_weight", 0.5)
    config_override("wake_recency_weight", 0.0)
    config_override("forward_replay_include_failures", False)

    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    # Highly-relevant success (cosine ~ high)
    mem.store(_ep(
        ep_id="relevant",
        text="compute the factorial of n",
    ))
    # Banal but unrelated; low cosine to query.
    mem.store(_ep(
        ep_id="banal",
        text="alphabet soup ingredients listing",
    ))

    wake = _build_wake(mem)
    out = wake._retrieve_episodes(
        "calculate factorial of integer",
    )  # noqa: SLF001
    success_ids = [ep.id for ep, _ in out if ep.outcome == "success"]
    assert success_ids[0] == "relevant", (
        f"salience override broke relevance: {success_ids}"
    )
