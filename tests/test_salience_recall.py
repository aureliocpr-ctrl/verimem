"""Tests for FORGIA pezzo #6: salience-weighted episode recall.

The plain top-k cosine recall in `EpisodicMemory.recall()` treats every
episode as equally informative — a banal success and a surprising failure
on the same kind of task have the same odds of being surfaced. The
hippocampus disagrees: prediction-error weighted replay is one of the
most replicated findings in memory neuroscience (Buzsáki 2015, Singer &
Frank 2009, Mattar & Daw 2018).

Three measurable invariants we test (declared BEFORE implementing):

  1. Salience computation:
     - Failure with outcome embedding far from "expected" gets HIGH score.
     - Success with outcome embedding near "expected" gets LOW score.

  2. Recall ranking:
     - With `salience_weight > 0`, a surprising failure ranks above a
       banal success at the same cosine relevance.
     - With `salience_weight = 0`, ranking degenerates to legacy cosine.

  3. Access tracking:
     - Every recall() updates `last_accessed_at` and `access_count` on
       the returned episodes (used by `replay_priority` in sleep.py).

Reconsolidation (the embedding-update-on-recall path) is INTENTIONALLY
NOT tested here — that's pezzo #7+ territory; the diagnosis agent
flagged it as a "tentazione resistita" because it breaks recall
idempotency for unclear payoff.
"""
from __future__ import annotations

import time

import pytest

from verimem.episode import Episode, Trace
from verimem.memory import EpisodicMemory


def _make_episode(
    *,
    id_: str,
    task_text: str,
    outcome: str = "success",
    final_answer: str = "ok",
    created_at: float | None = None,
) -> Episode:
    return Episode(
        id=id_,
        task_id=f"t_{id_}",
        task_text=task_text,
        outcome=outcome,
        final_answer=final_answer,
        created_at=created_at if created_at is not None else time.time(),
        traces=[Trace(
            step=1, thought="x", action="x", action_input="{}",
            observation="x",
        )],
    )


# ---------- Test 1: schema migration runs --------------------------------


def test_episodic_memory_v2_schema_has_salience_columns(tmp_path):
    """Schema v2 adds last_accessed_at, access_count, salience_score.
    Pre-existing v1 DBs migrate automatically without daorbits."""
    db = tmp_path / "ep.db"
    mem = EpisodicMemory(db_path=db)
    ep = _make_episode(id_="e1", task_text="fix arithmetic bug")
    mem.store(ep)

    # All three columns should exist and the row should round-trip.
    with mem._connect() as conn:
        cols = {r["name"] for r in conn.execute(
            "PRAGMA table_info(episodes)"
        ).fetchall()}
    assert "last_accessed_at" in cols
    assert "access_count" in cols
    assert "salience_score" in cols


# ---------- Test 2: salience scoring honours prediction error -------------


def test_surprising_failure_gets_high_salience(tmp_path):
    """Build a corpus of similar past successes ('fix calc.py' runs that
    end with a fix). Then store a failure on the same task family — the
    failure's outcome embedding is far from the established centroid,
    so its salience should be HIGH (>0.5)."""
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    # Five typical successes — these define what "expected" looks like
    for i in range(5):
        mem.store(_make_episode(
            id_=f"s{i}",
            task_text="fix arithmetic bug in calc.py",
            outcome="success",
            final_answer="patched calc.py with sign correction",
        ))
    # The surprising failure: same task, very different outcome
    surprise = _make_episode(
        id_="failure_x",
        task_text="fix arithmetic bug in calc.py",
        outcome="failure",
        final_answer="ERROR: dependency package missing",
    )
    mem.store(surprise)

    salience = mem.salience_of(surprise.id)
    assert salience >= 0.5, (
        f"surprising failure scored {salience:.3f} — "
        "prediction-error weighting isn't biting"
    )


def test_typical_success_gets_low_salience(tmp_path):
    """A success on the same task family with the same kind of answer
    as past episodes should score LOW salience — it teaches us nothing."""
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    for i in range(5):
        mem.store(_make_episode(
            id_=f"s{i}",
            task_text="fix arithmetic bug in calc.py",
            outcome="success",
            final_answer="patched calc.py with sign correction",
        ))
    typical = _make_episode(
        id_="typical_success",
        task_text="fix arithmetic bug in calc.py",
        outcome="success",
        final_answer="patched calc.py with sign correction",
    )
    mem.store(typical)

    salience = mem.salience_of(typical.id)
    assert salience <= 0.5, (
        f"typical success scored {salience:.3f} — "
        "salience should fade for redundant episodes"
    )


def test_first_episode_gets_neutral_salience(tmp_path):
    """The very first episode of a kind has no past for comparison —
    salience should be the neutral 0.5 default, not crash or score 0."""
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    first = _make_episode(id_="first", task_text="brand-new task family")
    mem.store(first)
    s = mem.salience_of(first.id)
    assert 0.4 <= s <= 0.6


# ---------- Test 3: recall ranking respects salience ----------------------


def test_recall_with_salience_weight_prefers_surprising_at_equal_relevance(
    tmp_path,
):
    """Two episodes with similar task_text (so similar cosine to the
    query) but different salience: with `salience_weight > 0` the
    surprising one ranks first."""
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    # Five typical successes to establish the "expected" centroid.
    for i in range(5):
        mem.store(_make_episode(
            id_=f"banal_{i}", task_text="fix calc.py arithmetic",
            outcome="success",
            final_answer="patched with sign correction",
        ))
    surprising = _make_episode(
        id_="surprising_failure",
        task_text="fix calc.py arithmetic",
        outcome="failure",
        final_answer="aborted: cannot import module",
    )
    mem.store(surprising)

    results = mem.recall(
        "fix calc.py arithmetic", k=3, salience_weight=0.5,
    )
    assert results, "recall returned empty unexpectedly"
    top_ids = [ep.id for ep, _ in results]
    assert "surprising_failure" in top_ids[:1], (
        f"with salience_weight=0.5, the surprising failure should "
        f"be top-ranked but ranking was {top_ids}"
    )


def test_legacy_recall_unchanged_when_salience_weight_zero(tmp_path):
    """`salience_weight=0` (the default) MUST preserve the pre-pezzo-#6
    behaviour: ranking is pure cosine top-k. This is the backward-compat
    contract for callers that don't opt in."""
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    mem.store(_make_episode(
        id_="far", task_text="completely unrelated task about UI",
    ))
    mem.store(_make_episode(
        id_="near", task_text="fix calc.py arithmetic",
    ))
    out_default = mem.recall("fix calc.py arithmetic", k=2)
    assert out_default[0][0].id == "near"


# ---------- Test 4: access tracking on recall ----------------------------


def test_recall_increments_access_count_and_last_accessed(tmp_path):
    """Every recall() bumps `access_count` and `last_accessed_at` on
    the returned episodes. This is the ONLY thing recall mutates —
    embedding stays untouched (reconsolidation is pezzo #7, not here)."""
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    ep = _make_episode(id_="e1", task_text="fix bug")
    mem.store(ep)

    before = mem.get(ep.id)
    assert before.access_count == 0
    assert before.last_accessed_at == 0.0

    t0 = time.time()
    mem.recall("fix bug", k=1)

    after = mem.get(ep.id)
    assert after.access_count == 1
    assert after.last_accessed_at >= t0


def test_recall_does_not_mutate_embedding(tmp_path):
    """Recall must NOT lerp the episode embedding toward the query.
    That would be reconsolidation — explicit non-goal of pezzo #6
    (see FORGIA.md: tentazione resistita per idempotency)."""
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    ep = _make_episode(id_="e1", task_text="fix bug in module X")
    mem.store(ep)

    # Embedding before
    with mem._connect() as conn:
        emb_before = conn.execute(
            "SELECT summary_embedding FROM episodes WHERE id = ?", (ep.id,),
        ).fetchone()["summary_embedding"]

    for _ in range(10):
        mem.recall("fix bug in module X", k=1)

    with mem._connect() as conn:
        emb_after = conn.execute(
            "SELECT summary_embedding FROM episodes WHERE id = ?", (ep.id,),
        ).fetchone()["summary_embedding"]

    assert emb_before == emb_after, (
        "recall mutated the summary_embedding — that's reconsolidation, "
        "explicitly out of scope for pezzo #6"
    )
