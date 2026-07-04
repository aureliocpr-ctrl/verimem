"""Tests for FORGIA pezzo #14: TCM cabling into EpisodicMemory.

Pezzo #12 forged the `ContextEngine` primitive (drifting context
vector, Howard & Kahana 2002). This pezzo wires it in:

  1. Schema v4 — `context_embedding BLOB` on episodes (NULL allowed).
  2. `Episode.context_embedding: bytes | None` field.
  3. `EpisodicMemory.store(ep, context_emb=...)` persists the context.
  4. `recall(query, ..., context_emb=..., context_weight=β)` adds
     `β · cosine(context_emb, ep.context_embedding)` to the score.

Tulving's encoding specificity (1973): retrieval is most effective
when the *current context* matches the *encoding context*. Two
episodes with the same task text but different surrounding contexts
deserve different retrieval rankings.

Six measurable invariants we test (declared BEFORE implementing):

  1. CONTEXT DISCRIMINATION:
     Two near-identical episodes stored with DIFFERENT contexts
     should get different scores when recall is given a query +
     context that matches one of them. The matching-context episode
     ranks first.

  2. NO-CONTEXT BACKWARD COMPAT:
     `recall(query)` without a context_emb returns identical results
     to legacy code (= cosine + salience + recency only).

  3. STORE PERSISTS CONTEXT:
     `store(episode, context_emb=ctx)` populates the column. NULL is
     valid for episodes stored without a context (legacy path).

  4. SCHEMA MIGRATION v3 → v4:
     A v3 DB opens cleanly with the new code: column added, existing
     rows keep NULL contexts (no false matches).

  5. CONTEXT WEIGHT MATH:
     With `context_weight=0.0` the score collapses to non-context
     ranking; with `context_weight=1.0` and identical contexts on the
     correct episode, the ranking matches reality.

  6. NULL-CONTEXT EPISODES SCORE NEUTRAL:
     Episodes with `context_embedding=NULL` get a neutral
     contribution (0.0) — they don't crash, they don't get
     spuriously promoted.
"""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path

import numpy as np

from engram.config import CONFIG
from engram.episode import Episode, Trace


def _ep(task_text: str, *, ep_id: str | None = None,
        final: str = "ok", outcome: str = "success") -> Episode:
    return Episode(
        id=ep_id or "",
        task_id=task_text[:30],
        task_text=task_text,
        traces=[Trace(step=1, thought="t", action="A", action_input="", observation="o")],
        outcome=outcome,  # type: ignore[arg-type]
        final_answer=final,
        tokens_used=1,
        skills_used=[],
        created_at=time.time(),
        notes="", critique="",
    )


def _normalize(v: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(v))
    return v / n if n > 0 else v


# ---------- Test 1: context discrimination ------------------------------


def test_recall_prefers_matching_context(tmp_path: Path):
    """Two episodes with near-identical summaries but different
    encoded contexts. A recall with the matching context should
    rank the right episode first."""
    from engram.memory import EpisodicMemory

    mem = EpisodicMemory(db_path=tmp_path / "ep.db")

    rng = np.random.default_rng(seed=11)
    ctx_a = _normalize(rng.standard_normal(CONFIG.embedding_dim).astype(np.float32))
    ctx_b = _normalize(rng.standard_normal(CONFIG.embedding_dim).astype(np.float32))

    # Same task text → near-identical summary embeddings.
    ep_a = _ep("retrieve customer order data", ep_id="ord-A")
    ep_b = _ep("retrieve customer order data", ep_id="ord-B")
    mem.store(ep_a, context_emb=ctx_a)
    mem.store(ep_b, context_emb=ctx_b)

    # Recall with context A — ord-A should win.
    res_a = mem.recall(
        "retrieve customer order data", k=2,
        context_emb=ctx_a, context_weight=0.5,
        track_access=False,
    )
    assert res_a, "no recall results"
    assert res_a[0][0].id == "ord-A", (
        f"context-A query didn't pick ord-A: top={res_a[0][0].id}"
    )

    # Recall with context B — ord-B should win.
    res_b = mem.recall(
        "retrieve customer order data", k=2,
        context_emb=ctx_b, context_weight=0.5,
        track_access=False,
    )
    assert res_b[0][0].id == "ord-B", (
        f"context-B query didn't pick ord-B: top={res_b[0][0].id}"
    )


# ---------- Test 2: backward compat (no context) -----------------------


def test_recall_without_context_unchanged(tmp_path: Path):
    """Legacy recall (no context kwargs) must give identical ordering
    to current behaviour. Aim: zero behavioural change for callers
    that don't opt in."""
    from engram.memory import EpisodicMemory

    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    for i, t in enumerate(["alpha task", "beta task", "gamma task"]):
        mem.store(_ep(t, ep_id=f"e{i}"))

    a = mem.recall("alpha task", k=3, track_access=False)
    b = mem.recall(
        "alpha task", k=3, context_weight=0.0, track_access=False,
    )
    assert [ep.id for ep, _ in a] == [ep.id for ep, _ in b]


# ---------- Test 3: store persists context -----------------------------


def test_store_persists_context_embedding(tmp_path: Path):
    """`store(ep, context_emb=ctx)` writes the BLOB to the new
    column."""
    from engram.memory import EpisodicMemory

    db = tmp_path / "ep.db"
    mem = EpisodicMemory(db_path=db)

    ctx = _normalize(np.ones(CONFIG.embedding_dim, dtype=np.float32))
    mem.store(_ep("hello", ep_id="h"), context_emb=ctx)

    with sqlite3.connect(db) as c:
        row = c.execute(
            "SELECT context_embedding FROM episodes WHERE id = 'h'"
        ).fetchone()
    assert row is not None
    assert row[0] is not None
    # 4 bytes per float32 × embedding_dim
    assert len(row[0]) == CONFIG.embedding_dim * 4

    # Without context_emb, the column stays NULL.
    mem.store(_ep("world", ep_id="w"))
    with sqlite3.connect(db) as c:
        row = c.execute(
            "SELECT context_embedding FROM episodes WHERE id = 'w'"
        ).fetchone()
    assert row[0] is None


# ---------- Test 4: schema migration v3 → v4 ---------------------------


def test_migration_v3_to_v4(tmp_path: Path):
    """A v3 DB (without context_embedding) auto-migrates to v4 on
    init."""
    from engram.memory import _EPISODES_SCHEMA_VERSION, EpisodicMemory

    db = tmp_path / "ep.db"

    mem1 = EpisodicMemory(db_path=db)
    mem1.store(_ep("alpha", ep_id="a"))
    del mem1

    # Roll back to v3 — drop every post-v3 column so v3+ migrations
    # can re-apply cleanly without "duplicate column" errors.
    conn = sqlite3.connect(db)
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(episodes)")}
        for col in ("context_embedding", "pinned"):
            if col in cols:
                conn.execute(f"ALTER TABLE episodes DROP COLUMN {col}")
        conn.execute(
            "UPDATE _schema_version SET version = 3 WHERE db_id = 'episodes'"
        )
        conn.commit()
    finally:
        conn.close()

    mem2 = EpisodicMemory(db_path=db)
    with sqlite3.connect(db) as c:
        cols = {r[1] for r in c.execute("PRAGMA table_info(episodes)")}
        v = c.execute(
            "SELECT version FROM _schema_version WHERE db_id='episodes'"
        ).fetchone()[0]
    assert "context_embedding" in cols
    assert v == _EPISODES_SCHEMA_VERSION
    # Pre-existing episode reads back fine, just with NULL context.
    out = mem2.recall("alpha", k=1, track_access=False)
    assert out and out[0][0].id == "a"


# ---------- Test 5: context_weight=0 collapses to legacy ---------------


def test_context_weight_zero_collapses_to_no_context(tmp_path: Path):
    """`context_weight=0.0` should give the same score as not passing
    a context at all — even with a context_emb provided."""
    from engram.memory import EpisodicMemory

    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    rng = np.random.default_rng(seed=3)
    ctx = _normalize(rng.standard_normal(CONFIG.embedding_dim).astype(np.float32))
    for i, t in enumerate(["task one", "task two", "task three"]):
        mem.store(_ep(t, ep_id=f"e{i}"), context_emb=ctx)

    a = mem.recall("task one", k=3, track_access=False)
    b = mem.recall(
        "task one", k=3, context_emb=ctx, context_weight=0.0,
        track_access=False,
    )
    assert [ep.id for ep, _ in a] == [ep.id for ep, _ in b]


# ---------- Test 6: null contexts score neutrally ----------------------


def test_null_context_episodes_score_neutral(tmp_path: Path):
    """Episodes stored without a context_emb (NULL column) must not
    crash recall and must not be spuriously promoted by the context
    boost — they get a 0 contribution."""
    from engram.memory import EpisodicMemory

    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    rng = np.random.default_rng(seed=7)
    ctx = _normalize(rng.standard_normal(CONFIG.embedding_dim).astype(np.float32))

    # ep "with-ctx": stored with context that EXACTLY matches the query ctx
    # ep "no-ctx": stored without context. Both have similar task text.
    mem.store(_ep("doc retrieval task", ep_id="with-ctx"), context_emb=ctx)
    mem.store(_ep("doc retrieval task", ep_id="no-ctx"))  # NULL context

    out = mem.recall(
        "doc retrieval task", k=2,
        context_emb=ctx, context_weight=1.0,
        track_access=False,
    )
    assert len(out) == 2
    # The matching context wins.
    assert out[0][0].id == "with-ctx", (
        f"context match should rank first; got {[ep.id for ep, _ in out]}"
    )
