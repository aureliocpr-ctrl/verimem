"""Tests for FORGIA pezzo #21: `recall_by_context` API.

Pezzo #14 added `recall(query, context_emb=...)` — but the API
still REQUIRES a task_text. This pezzo adds a sister method
`recall_by_context(context_emb, k)` that ranks ONLY by cosine on
the encoding context column. Useful when:

  - The current "where am I" cue is the only cue available.
  - Debug / observability — replay all episodes encoded under
    similar contexts.
  - Future "lookaround" stage where the agent samples past
    episodes by context BEFORE generating a task.

Three measurable invariants:

  1. RANKS BY CONTEXT COSINE: episodes stored with similar
     context_embeddings score higher than ones with dissimilar
     contexts.

  2. NULL-CONTEXT EXCLUDED: episodes without a stored context are
     not returned (NULL is not 0-cosine, it's absent — explicit).

  3. EMPTY CORPUS / EMPTY CONTEXTS: returns [] gracefully. No
     crash.
"""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np

from verimem.config import CONFIG
from verimem.episode import Episode, Trace


def _ep(*, ep_id: str, text: str = "task") -> Episode:
    return Episode(
        id=ep_id, task_id=text[:30], task_text=text,
        outcome="success", final_answer="ok",
        traces=[Trace(step=1, thought="t", action="A",
                      action_input="", observation="o")],
        tokens_used=1, skills_used=[],
        created_at=time.time(),
    )


def _normalize(v: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(v))
    return v / n if n > 0 else v


# ---------- Test 1: ranks by context cosine ----------------------------


def test_recall_by_context_ranks_by_context_cosine(tmp_path: Path):
    """Among 3 episodes with distinct context vectors, the one whose
    context most-resembles the query context ranks first."""
    from verimem.memory import EpisodicMemory

    mem = EpisodicMemory(db_path=tmp_path / "ep.db")

    rng = np.random.default_rng(seed=11)
    ctx_a = _normalize(rng.standard_normal(CONFIG.embedding_dim).astype(np.float32))
    ctx_b = _normalize(rng.standard_normal(CONFIG.embedding_dim).astype(np.float32))
    ctx_c = _normalize(rng.standard_normal(CONFIG.embedding_dim).astype(np.float32))

    mem.store(_ep(ep_id="A"), context_emb=ctx_a)
    mem.store(_ep(ep_id="B"), context_emb=ctx_b)
    mem.store(_ep(ep_id="C"), context_emb=ctx_c)

    out = mem.recall_by_context(ctx_a, k=3)
    assert out, "no results"
    assert out[0][0].id == "A", (
        f"matching context didn't rank first: {[ep.id for ep, _ in out]}"
    )


# ---------- Test 2: null contexts excluded ----------------------------


def test_recall_by_context_excludes_null_contexts(tmp_path: Path):
    """Episodes stored without a context_emb (NULL column) are not
    returned by `recall_by_context` — there's no signal to score them."""
    from verimem.memory import EpisodicMemory

    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    rng = np.random.default_rng(seed=23)
    ctx = _normalize(rng.standard_normal(CONFIG.embedding_dim).astype(np.float32))

    mem.store(_ep(ep_id="with-ctx"), context_emb=ctx)
    mem.store(_ep(ep_id="no-ctx"))  # NULL context

    out = mem.recall_by_context(ctx, k=5)
    out_ids = {ep.id for ep, _ in out}
    assert out_ids == {"with-ctx"}, (
        f"null-context episode appeared in results: {out_ids}"
    )


# ---------- Test 3: empty graceful handling ---------------------------


def test_recall_by_context_empty_corpus(tmp_path: Path):
    """Empty memory or no-context episodes returns []."""
    from verimem.memory import EpisodicMemory

    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    rng = np.random.default_rng(seed=7)
    ctx = _normalize(rng.standard_normal(CONFIG.embedding_dim).astype(np.float32))

    # Empty
    assert mem.recall_by_context(ctx, k=5) == []

    # Only no-ctx episodes
    mem.store(_ep(ep_id="x"))
    mem.store(_ep(ep_id="y"))
    assert mem.recall_by_context(ctx, k=5) == []


# ---------- Test 4: dimension mismatch raises -------------------------


def test_recall_by_context_dim_mismatch_raises(tmp_path: Path):
    """Passing the wrong-dim context vector should fail loudly, not
    silently return wrong rankings."""
    import pytest as _pytest

    from verimem.memory import EpisodicMemory

    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    bad = np.zeros(CONFIG.embedding_dim + 16, dtype=np.float32)
    with _pytest.raises(ValueError, match="dim"):
        mem.recall_by_context(bad, k=5)


# ---------- Test 5: top_k respected ----------------------------------


def test_recall_by_context_returns_at_most_k(tmp_path: Path):
    """k=2 returns at most 2 results even when more match."""
    from verimem.memory import EpisodicMemory

    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    rng = np.random.default_rng(seed=42)
    base = _normalize(rng.standard_normal(CONFIG.embedding_dim).astype(np.float32))
    for i in range(5):
        # All similar contexts (small perturbation).
        perturb = rng.standard_normal(CONFIG.embedding_dim).astype(np.float32) * 0.05
        ctx = _normalize(base + perturb)
        mem.store(_ep(ep_id=f"e{i}"), context_emb=ctx)

    out = mem.recall_by_context(base, k=2)
    assert len(out) == 2
