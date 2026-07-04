"""Tests for FORGIA pezzo #22: WakeAgent context lifecycle API.

Pezzo #17 added a long-lived ContextEngine that drifts permanently
across run() invocations. For batch/parallel/test isolation we need
explicit lifecycle control:

  - `wake.reset_context()`: snap to zero (boot state).
  - `wake.checkpoint_context() -> np.ndarray`: snapshot current state.
  - `wake.restore_context(state)`: load a snapshot.

Five measurable invariants:

  1. RESET TO ZERO: after reset() the engine state has zero norm.

  2. CHECKPOINT IS A COPY: mutating the returned array doesn't
     affect the engine.

  3. RESTORE WORKS: after `s = checkpoint(); ...drift...; restore(s)`,
     engine state equals s.

  4. RESTORE VALIDATES DIM: passing a wrong-dim vector raises.

  5. CHECKPOINT/RESTORE ROUNDTRIP: state(after restore(checkpoint))
     == state(before).
"""
from __future__ import annotations

import numpy as np
import pytest

from engram.config import CONFIG
from engram.context_engine import ContextEngine


def _build_wake_with_engine():
    """A minimally-wired WakeAgent with a ContextEngine — same shape
    as `WakeAgent.__init__` but skipping the LLM/tool wiring."""
    from engram.wake import WakeAgent
    wake = object.__new__(WakeAgent)
    wake._context_engine = ContextEngine(  # type: ignore[attr-defined]
        dim=CONFIG.embedding_dim, rho=CONFIG.tcm_rho,
    )
    return wake


def _normalize(v: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(v))
    return v / n if n > 0 else v


# ---------- Test 1: reset_context() ------------------------------------


def test_reset_context_returns_engine_to_zero():
    wake = _build_wake_with_engine()
    rng = np.random.default_rng(seed=11)
    wake._context_engine.observe(  # noqa: SLF001
        _normalize(rng.standard_normal(CONFIG.embedding_dim).astype(np.float32))
    )
    assert float(np.linalg.norm(wake._context_engine.state)) > 0.0  # noqa: SLF001
    wake.reset_context()
    assert float(np.linalg.norm(wake._context_engine.state)) == 0.0  # noqa: SLF001


# ---------- Test 2: checkpoint is a copy ------------------------------


def test_checkpoint_returns_independent_copy():
    wake = _build_wake_with_engine()
    rng = np.random.default_rng(seed=23)
    wake._context_engine.observe(  # noqa: SLF001
        _normalize(rng.standard_normal(CONFIG.embedding_dim).astype(np.float32))
    )
    snap = wake.checkpoint_context()
    snap[:] = 0.0  # mutate the returned array
    # Engine state must be unaffected.
    assert float(np.linalg.norm(wake._context_engine.state)) > 0.0  # noqa: SLF001


# ---------- Test 3: restore -------------------------------------------


def test_restore_context_loads_snapshot():
    wake = _build_wake_with_engine()
    rng = np.random.default_rng(seed=42)
    wake._context_engine.observe(  # noqa: SLF001
        _normalize(rng.standard_normal(CONFIG.embedding_dim).astype(np.float32))
    )
    snap = wake.checkpoint_context()

    # Drift further.
    wake._context_engine.observe(  # noqa: SLF001
        _normalize(rng.standard_normal(CONFIG.embedding_dim).astype(np.float32))
    )
    drifted = wake._context_engine.state.copy()  # noqa: SLF001
    assert not np.array_equal(drifted, snap)

    # Restore.
    wake.restore_context(snap)
    assert np.array_equal(wake._context_engine.state, snap)  # noqa: SLF001


# ---------- Test 4: restore validates dim -----------------------------


def test_restore_context_validates_dim():
    wake = _build_wake_with_engine()
    bad = np.zeros(CONFIG.embedding_dim + 16, dtype=np.float32)
    with pytest.raises(ValueError, match="dim"):
        wake.restore_context(bad)


# ---------- Test 5: roundtrip ----------------------------------------


def test_checkpoint_restore_roundtrip():
    wake = _build_wake_with_engine()
    rng = np.random.default_rng(seed=99)
    for _ in range(3):
        wake._context_engine.observe(  # noqa: SLF001
            _normalize(
                rng.standard_normal(CONFIG.embedding_dim).astype(np.float32)
            )
        )
    before = wake._context_engine.state.copy()  # noqa: SLF001
    snap = wake.checkpoint_context()
    wake.reset_context()
    assert float(np.linalg.norm(wake._context_engine.state)) == 0.0  # noqa: SLF001
    wake.restore_context(snap)
    assert np.array_equal(wake._context_engine.state, before)  # noqa: SLF001
