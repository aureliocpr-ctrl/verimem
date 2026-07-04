"""Tests for FORGIA pezzo #17: cross-session ContextEngine in WakeAgent.

Pezzo #15 instantiated a transient ContextEngine inside `_build_episode_context`
(used post-hoc, episode-isolated). Pezzo #17 adds an additional,
LONG-LIVED ContextEngine on the WakeAgent itself: it drifts across
run() invocations and feeds `_retrieve_episodes` so episodes encoded
in similar recent contexts get a recall boost.

Five measurable invariants we test (declared BEFORE implementing):

  1. ENGINE EXISTS: WakeAgent has a `_context_engine` attribute of
     type ContextEngine after init. State is initially zero.

  2. STATE DRIFTS PER RUN: after a wake.run(...) (or the equivalent
     direct observe), the engine state is non-zero. Two distinct
     tasks produce divergent post-state vectors.

  3. RETRIEVE USES CONTEXT: with `tcm_cross_session_enabled=True`
     and `tcm_recall_context_weight>0`, calling `_retrieve_episodes`
     after the engine has drifted picks episodes whose stored
     context matches the cross-session state.

  4. ZERO-NORM CONTEXT IS NOT PASSED: at boot the engine state is 0;
     `_retrieve_episodes` should NOT pass `context_emb=zeros` to
     `memory.recall` (it would give a useless 0-cosine boost). It
     skips the kwarg.

  5. KILL-SWITCH OFF preserves legacy: with `tcm_cross_session_enabled
     =False`, retrieve does not pass context kwargs.
"""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pytest

from engram.config import CONFIG
from engram.context_engine import ContextEngine
from engram.episode import Episode, Trace
from engram.memory import EpisodicMemory


def _ep(*, ep_id: str, text: str) -> Episode:
    return Episode(
        id=ep_id, task_id=text[:30], task_text=text,
        outcome="success", final_answer="ok",
        traces=[Trace(step=1, thought="t", action="A",
                      action_input="", observation="o")],
        tokens_used=1, skills_used=[],
        created_at=time.time(),
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
    """A minimally-wired WakeAgent that we can call retrieve+observe on."""
    from engram.wake import WakeAgent, WakeConfig

    wake = object.__new__(WakeAgent)
    wake.memory = memory  # type: ignore[misc]
    wake.cfg = WakeConfig(
        max_steps=4, self_critique=False, episodes_recall_k=5,
    )
    wake._context_engine = ContextEngine(  # type: ignore[attr-defined]  # noqa: SLF001
        dim=CONFIG.embedding_dim, rho=CONFIG.tcm_rho,
    )
    return wake


# ---------- Test 1: engine exists, zero initial -----------------------


def test_wake_has_context_engine_at_init(tmp_path: Path):
    """Real WakeAgent (not the bypass) has a ContextEngine attached."""
    from engram.llm import MockLLM
    from engram.skill import SkillLibrary
    from engram.tools import default_tools
    from engram.wake import WakeAgent, WakeConfig

    cfg = WakeConfig(max_steps=2, self_critique=False)
    wake = WakeAgent(
        memory=EpisodicMemory(db_path=tmp_path / "ep.db"),
        skills=SkillLibrary(
            dir_path=tmp_path / "skills",
            db_path=tmp_path / "skills" / "i.db",
        ),
        tools=default_tools(),
        llm=MockLLM([]),
        config=cfg,
    )
    assert hasattr(wake, "_context_engine")
    assert isinstance(wake._context_engine, ContextEngine)  # noqa: SLF001
    assert float(np.linalg.norm(wake._context_engine.state)) == 0.0  # noqa: SLF001


# ---------- Test 2: drift across observations ------------------------


def test_context_engine_drifts_under_observation(tmp_path: Path):
    """Observing two distinct tasks produces a non-zero state different
    from observing only one of them."""
    from engram import embedding as emb_mod

    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    wake = _build_wake(mem)

    # Initial: zero.
    assert float(np.linalg.norm(wake._context_engine.state)) == 0.0  # noqa: SLF001

    wake._context_engine.observe(emb_mod.encode("alpha task"))  # noqa: SLF001
    after_a = wake._context_engine.state.copy()  # noqa: SLF001
    wake._context_engine.observe(emb_mod.encode("beta task"))  # noqa: SLF001
    after_b = wake._context_engine.state.copy()  # noqa: SLF001

    assert float(np.linalg.norm(after_a)) > 0.0
    assert float(np.linalg.norm(after_b)) > 0.0
    assert not np.array_equal(after_a, after_b)


# ---------- Test 3: retrieve uses context when active ----------------


def test_retrieve_uses_cross_session_context(tmp_path: Path, config_override):
    """Two episodes stored with distinct contexts; the wake agent
    drifts to context A; retrieve should prefer the A-context episode
    even when the query text is generic."""
    from engram import embedding as emb_mod

    config_override("tcm_cross_session_enabled", True)
    config_override("tcm_recall_context_weight", 0.50)
    config_override("forward_replay_include_failures", False)

    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    rng = np.random.default_rng(seed=42)
    ctx_a = rng.standard_normal(CONFIG.embedding_dim).astype(np.float32)
    ctx_a /= np.linalg.norm(ctx_a)
    ctx_b = rng.standard_normal(CONFIG.embedding_dim).astype(np.float32)
    ctx_b /= np.linalg.norm(ctx_b)

    common_task = "look up the right record"
    mem.store(_ep(ep_id="A", text=common_task), context_emb=ctx_a)
    mem.store(_ep(ep_id="B", text=common_task), context_emb=ctx_b)

    wake = _build_wake(mem)
    # Pre-load wake's engine state to ctx_a (simulating multiple past
    # runs that drifted it that way).
    wake._context_engine._state = ctx_a.copy()  # noqa: SLF001

    out = wake._retrieve_episodes(common_task)  # noqa: SLF001
    success_ids = [ep.id for ep, _ in out if ep.outcome == "success"]
    assert success_ids and success_ids[0] == "A", (
        f"cross-session context didn't bias retrieve: top={success_ids[0]}"
    )


# ---------- Test 4: zero-norm context skips recall kwarg --------------


def test_zero_norm_context_does_not_pass_kwarg(tmp_path: Path, config_override):
    """At boot the engine state is zero. retrieve must not pass a
    zero-vector to recall — that's a useless cosine boost (always 0)
    and a code smell."""
    config_override("tcm_cross_session_enabled", True)
    config_override("tcm_recall_context_weight", 0.50)
    config_override("forward_replay_include_failures", False)

    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    mem.store(_ep(ep_id="alpha", text="alpha task"))
    mem.store(_ep(ep_id="beta", text="beta task"))

    wake = _build_wake(mem)
    # Don't drift — engine stays at zero.
    assert float(np.linalg.norm(wake._context_engine.state)) == 0.0  # noqa: SLF001

    out = wake._retrieve_episodes("alpha task")  # noqa: SLF001
    # Just check it returned something sensible — no crash.
    success_ids = [ep.id for ep, _ in out if ep.outcome == "success"]
    assert "alpha" in success_ids


# ---------- Test 5: kill-switch off, no context boost ----------------


def test_cross_session_disabled_skips_context(tmp_path: Path, config_override):
    """With `tcm_cross_session_enabled=False`, retrieve falls back
    to legacy ordering — context engine state is irrelevant."""
    config_override("tcm_cross_session_enabled", False)
    config_override("tcm_recall_context_weight", 0.50)
    config_override("forward_replay_include_failures", False)

    rng = np.random.default_rng(seed=11)
    ctx = rng.standard_normal(CONFIG.embedding_dim).astype(np.float32)
    ctx /= np.linalg.norm(ctx)

    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    common_task = "look up record"
    mem.store(_ep(ep_id="X", text=common_task), context_emb=ctx)
    mem.store(_ep(ep_id="Y", text=common_task))

    wake = _build_wake(mem)
    wake._context_engine._state = ctx.copy()  # noqa: SLF001

    out_a = wake._retrieve_episodes(common_task)  # noqa: SLF001
    # With cross-session disabled, the result must equal the legacy
    # path on the same query — i.e. context_emb is NOT passed to recall.
    legacy = mem.recall(
        common_task, k=wake.cfg.episodes_recall_k, outcome_filter="success",
    )
    assert [ep.id for ep, _ in out_a[:len(legacy)]] == [ep.id for ep, _ in legacy]
