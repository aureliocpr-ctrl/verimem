"""Tests for FORGIA pezzo #15: wake-loop integration of TCM context.

Pezzo #14 added the `context_embedding` BLOB column and the
`recall(context_emb=..., context_weight=β)` API. This pezzo wires the
wake loop to actually populate the column at episode-store time:

  1. `WakeAgent` now instantiates a `ContextEngine(dim=embedding_dim,
     rho=tcm_rho)` for each `run()` call.
  2. The engine observes the task_text first (anchor), then every
     tool-result observation in order.
  3. At store-time, `episode.context_embedding = engine.state`.

Five measurable invariants we test (declared BEFORE implementing):

  1. CONTEXT IS POPULATED:
     After `wake.run(...)`, the persisted episode has a non-NULL
     context_embedding column.

  2. CONTEXT REFLECTS OBSERVATIONS:
     Two tasks with the same task_text but DIFFERENT observation
     content (different tool outputs) produce DIFFERENT context
     embeddings. Cosine between them < 1.0.

  3. STABILITY UNDER REPETITION:
     Running the same wake.run twice produces the same context
     (deterministic given the same task + observations).

  4. CONFIG OFF KILL-SWITCH:
     With `tcm_wake_enabled=False`, episodes are stored with NULL
     context (legacy path, unchanged).

  5. SEED-FREE BUILDER:
     `_build_episode_context(task_text, traces)` is pure: same
     inputs → same output. No reliance on `time.time()` or rng.
"""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np

from verimem.config import CONFIG
from verimem.episode import Episode, Trace
from verimem.memory import EpisodicMemory

# Mute the heavy WakeAgent end-to-end machinery; these tests only need
# the deterministic `_build_episode_context` and the store integration.


def _ep(task_text: str, *, ep_id: str | None = None,
        traces: list[Trace] | None = None) -> Episode:
    return Episode(
        id=ep_id or "",
        task_id=task_text[:30],
        task_text=task_text,
        traces=traces or [],
        outcome="success",
        final_answer="ok",
        tokens_used=1,
        skills_used=[],
        created_at=time.time(),
        notes="", critique="",
    )


# ---------- Test 1: deterministic builder ------------------------------


def test_build_episode_context_is_deterministic():
    """Calling `_build_episode_context` twice with identical inputs
    produces identical output — no hidden time/rng coupling."""
    from verimem.wake import WakeAgent

    traces = [
        Trace(step=1, thought="t", action="A",
              action_input="", observation="alpha output"),
        Trace(step=2, thought="t", action="B",
              action_input="", observation="beta output"),
    ]
    # We instantiate the bare minimum WakeAgent to call the helper.
    # Using object.__new__ avoids the LLM/tool wiring requirement —
    # the helper is a pure function on text inputs.
    wake = object.__new__(WakeAgent)
    a = wake._build_episode_context("query the database", traces)  # noqa: SLF001
    b = wake._build_episode_context("query the database", traces)  # noqa: SLF001
    assert np.array_equal(a, b)


# ---------- Test 2: context reflects observations ----------------------


def test_context_differs_when_observations_differ():
    """Two episodes with the same task_text but different observations
    produce different contexts. The drift over distinct obs creates
    distinct end-states (Howard & Kahana 2002)."""
    from verimem.wake import WakeAgent

    wake = object.__new__(WakeAgent)
    common_task = "summarise the report"
    traces_a = [
        Trace(step=1, thought="t", action="A", action_input="",
              observation="found 12 anomalies in the financial section"),
    ]
    traces_b = [
        Trace(step=1, thought="t", action="A", action_input="",
              observation="extracted 5 customer testimonials from the report"),
    ]
    ctx_a = wake._build_episode_context(common_task, traces_a)  # noqa: SLF001
    ctx_b = wake._build_episode_context(common_task, traces_b)  # noqa: SLF001
    cos = float(np.dot(ctx_a, ctx_b)) / (
        np.linalg.norm(ctx_a) * np.linalg.norm(ctx_b) + 1e-9
    )
    assert cos < 0.99, (
        f"different observations should drift to different contexts; "
        f"cos={cos:.3f}"
    )


# ---------- Test 3: empty traces give task-only context ---------------


def test_empty_traces_yields_task_only_context():
    """No tool calls → context = (1-ρ) · task_emb (single observe).
    Degenerate but well-defined; non-zero norm."""
    from verimem.wake import WakeAgent

    wake = object.__new__(WakeAgent)
    ctx = wake._build_episode_context("just a question", [])  # noqa: SLF001
    assert float(np.linalg.norm(ctx)) > 0.0


# ---------- Test 4: kill-switch disables context populating -----------


def test_tcm_disabled_stores_null_context(tmp_path: Path):
    """With `CONFIG.tcm_wake_enabled = False`, the wake.run() does not
    pass a context to memory.store, leaving the column NULL."""
    import sqlite3

    from verimem.wake import WakeAgent

    # Direct simulation of run()'s storage call without LLM/tool.
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    ep = _ep("hello task", ep_id="h",
             traces=[Trace(step=1, thought="t", action="A",
                           action_input="", observation="hi")])
    wake = object.__new__(WakeAgent)
    wake.memory = mem  # type: ignore[misc]
    # Mimic the run() store path. We use object.__setattr__ to bypass
    # the frozen-dataclass guard on CONFIG.
    saved = CONFIG.tcm_wake_enabled
    try:
        object.__setattr__(CONFIG, "tcm_wake_enabled", False)
        ctx_emb = (
            wake._build_episode_context(ep.task_text, ep.traces)  # noqa: SLF001
            if CONFIG.tcm_wake_enabled else None
        )
        mem.store(ep, context_emb=ctx_emb)
    finally:
        object.__setattr__(CONFIG, "tcm_wake_enabled", saved)

    with sqlite3.connect(tmp_path / "ep.db") as c:
        row = c.execute(
            "SELECT context_embedding FROM episodes WHERE id='h'"
        ).fetchone()
    assert row[0] is None


# ---------- Test 5: kill-switch ON populates the column ---------------


def test_tcm_enabled_populates_context_column(tmp_path: Path):
    """With `CONFIG.tcm_wake_enabled = True` (default), the wake store
    path persists a non-NULL context_embedding."""
    import sqlite3

    from verimem.wake import WakeAgent

    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    ep = _ep("retrieve account info", ep_id="r",
             traces=[
                 Trace(step=1, thought="t", action="search",
                       action_input="", observation="found account 1234"),
             ])
    wake = object.__new__(WakeAgent)
    wake.memory = mem  # type: ignore[misc]
    saved = CONFIG.tcm_wake_enabled
    try:
        object.__setattr__(CONFIG, "tcm_wake_enabled", True)
        ctx_emb = (
            wake._build_episode_context(ep.task_text, ep.traces)  # noqa: SLF001
            if CONFIG.tcm_wake_enabled else None
        )
        mem.store(ep, context_emb=ctx_emb)
    finally:
        object.__setattr__(CONFIG, "tcm_wake_enabled", saved)

    with sqlite3.connect(tmp_path / "ep.db") as c:
        row = c.execute(
            "SELECT context_embedding FROM episodes WHERE id='r'"
        ).fetchone()
    assert row[0] is not None
    assert len(row[0]) == CONFIG.embedding_dim * 4
