"""Tests for FORGIA pezzo #5: `consider_episodes` — weighted choice
between past episodes (failures or successes) when one must be picked
to anchor a forward-replay block, an avoid-path block, or a divergence
alignment.

Today the wake loop picks `failed_for_skill[0]` arbitrarily and uses
token-overlap to pick the success-twin in `_divergence_block`. Both
choices ignore:

  - **Recency**: a failure from yesterday tells us more about the
    current state of the system than one from three months ago — the
    skill library has evolved in between.
  - **Cosine relevance**: token-overlap is a weak proxy for semantic
    similarity. The real signal lives in the embedding space.

`consider_episodes` is the gemello of `consider_skills`: a primitive
that scores a candidate set by a composable combination of relevance
and recency, then returns them ranked.

Three invariants:

  1. At equal recency, higher cosine wins.
  2. At equal cosine, more recent wins.
  3. Empty input → empty output. No crashes.
"""
from __future__ import annotations

import math
import time

import numpy as np
import pytest

from verimem.episode import Episode
from verimem.selection import EpisodeChoice, consider_episodes


def _unit(v: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(v))
    return v / n if n > 0 else v


def _make_ep(
    id_: str, *,
    task_text: str = "task",
    outcome: str = "failure",
    created_at: float | None = None,
) -> Episode:
    return Episode(
        id=id_, task_id="t", task_text=task_text, outcome=outcome,
        created_at=created_at if created_at is not None else time.time(),
    )


# ---------- Test 1: at equal recency, relevance decides ------------------


def test_higher_cosine_wins_at_equal_recency():
    now = 1_700_000_000.0  # fixed for determinism
    related = _make_ep("e_related", task_text="fix arithmetic bug",
                       created_at=now)
    unrelated = _make_ep("e_unrelated", task_text="deploy frontend",
                         created_at=now)

    task_emb = _unit(np.array([1.0, 0.0, 0.0], dtype=np.float32))
    embs = {
        "e_related": _unit(np.array([0.95, 0.31, 0.0], dtype=np.float32)),
        "e_unrelated": _unit(np.array([0.0, 1.0, 0.0], dtype=np.float32)),
    }

    choices = consider_episodes(
        [related, unrelated], task_emb,
        episode_embeddings=embs, now=now,
    )
    assert choices[0].episode.id == "e_related"


# ---------- Test 2: at equal relevance, recency decides ------------------


def test_more_recent_wins_at_equal_relevance():
    now = 1_700_000_000.0
    recent = _make_ep("e_recent", created_at=now - 60)  # 1 min ago
    old = _make_ep("e_old", created_at=now - 30 * 86400)  # 30 days ago

    task_emb = _unit(np.array([1.0, 0.0, 0.0], dtype=np.float32))
    same = _unit(np.array([0.9, 0.43, 0.0], dtype=np.float32))
    embs = {"e_recent": same, "e_old": same}

    choices = consider_episodes(
        [recent, old], task_emb,
        episode_embeddings=embs, now=now,
        recency_weight=0.3, recency_tau_s=7 * 86400,  # 7-day half-life-ish
    )
    assert choices[0].episode.id == "e_recent"


# ---------- Test 3: empty input ------------------------------------------


def test_empty_input_returns_empty():
    out = consider_episodes(
        [], np.array([1.0, 0.0, 0.0], dtype=np.float32),
        episode_embeddings={}, now=time.time(),
    )
    assert out == []


# ---------- Test 4: recency_weight=0 → degenerates to similarity ranking --


def test_recency_weight_zero_uses_cosine_only():
    """With recency_weight=0 the ranking is identical to cosine top-k.
    This is the backward-compat regime — useful when episodes are
    short-lived (tests, ephemeral runs) and recency is meaningless."""
    now = 1_700_000_000.0
    fresh_far = _make_ep(
        "e_fresh_far", task_text="x", created_at=now,
    )
    old_close = _make_ep(
        "e_old_close", task_text="y", created_at=now - 365 * 86400,
    )
    task_emb = _unit(np.array([1.0, 0.0, 0.0], dtype=np.float32))
    embs = {
        "e_fresh_far": _unit(np.array([0.2, 0.98, 0.0], dtype=np.float32)),
        "e_old_close": _unit(np.array([0.95, 0.31, 0.0], dtype=np.float32)),
    }
    choices = consider_episodes(
        [fresh_far, old_close], task_emb,
        episode_embeddings=embs, now=now,
        recency_weight=0.0,
    )
    # old_close has higher cosine — wins despite being a year old.
    assert choices[0].episode.id == "e_old_close"


# ---------- Test 5: choices carry the diagnostic fields ------------------


def test_choice_records_carry_relevance_recency_score():
    """`EpisodeChoice` is the observability hook — same convention as
    `Choice` in pezzo #1."""
    now = 1_700_000_000.0
    ep = _make_ep("e", created_at=now - 3600)
    task_emb = _unit(np.array([1.0, 0.0, 0.0], dtype=np.float32))
    embs = {"e": _unit(np.array([0.7, 0.7, 0.0], dtype=np.float32))}
    choices = consider_episodes(
        [ep], task_emb, episode_embeddings=embs, now=now,
        recency_weight=0.3, recency_tau_s=7 * 86400,
    )
    c = choices[0]
    assert isinstance(c, EpisodeChoice)
    assert c.episode.id == "e"
    assert 0.0 <= c.relevance <= 1.0
    assert 0.0 <= c.recency <= 1.0
    # Score is a documented affine combination
    expected = c.relevance + 0.3 * c.recency
    assert math.isclose(c.score, expected, rel_tol=1e-6)


# ---------- Test 6: missing embedding for an episode raises --------------


def test_missing_episode_embedding_raises():
    """No silent zero-fallback. If we don't have an embedding for an
    episode, we don't know its relevance — bail out loudly."""
    ep = _make_ep("ghost", created_at=time.time())
    task_emb = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    with pytest.raises(KeyError, match="ghost"):
        consider_episodes([ep], task_emb, episode_embeddings={},
                          now=time.time())


# ---------- Test 7: realistic mix — relevance and recency compete --------


def test_realistic_mix_relevance_outweighs_old_recency():
    """The default weighting (recency_weight=0.3) means cosine still
    dominates — a clearly more relevant old failure beats a barely
    relevant fresh one. Recency is a tiebreaker, not the lead signal."""
    now = 1_700_000_000.0
    old_relevant = _make_ep("e_old_rel", created_at=now - 14 * 86400)
    fresh_irrelevant = _make_ep("e_fresh_irrel", created_at=now)

    task_emb = _unit(np.array([1.0, 0.0, 0.0], dtype=np.float32))
    embs = {
        "e_old_rel": _unit(np.array([0.95, 0.31, 0.0], dtype=np.float32)),
        "e_fresh_irrel": _unit(np.array([0.30, 0.95, 0.0], dtype=np.float32)),
    }
    choices = consider_episodes(
        [old_relevant, fresh_irrelevant], task_emb,
        episode_embeddings=embs, now=now,
        recency_weight=0.3, recency_tau_s=7 * 86400,
    )
    # Cosine gap (0.65) >> recency gap (~0.3 * 0.13 = 0.04). Relevance wins.
    assert choices[0].episode.id == "e_old_rel"
