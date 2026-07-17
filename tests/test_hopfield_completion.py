"""Tests for FORGIA pezzo #10: Modern Hopfield pattern completion.

Ramsauer et al. (2020) "Hopfield Networks is All You Need"
(arXiv:2008.02217) showed that Hopfield networks with the right energy
function are equivalent to self-attention and enable exponential
storage capacity. Concretely:

    completed = M.T @ softmax(β · M @ cue)

where `M` is the pattern matrix (episode summaries here) and `cue` is
a (possibly partial) query vector. The result is the *pattern
completion*: a vector that is itself a soft mixture of stored patterns
weighted by attention to the cue.

For HippoAgent this gives a complementary recall path to cosine top-k:

  - Cosine top-k: returns ranked existing episodes by cosine to a query.
  - Hopfield completion: returns the *attention weights* over the
    pattern matrix, surfacing the few episodes the cue is converging
    onto. With β high → attention concentrates on the closest match
    (≈ argmax). With β low → attention spreads (= a soft prior over
    similar episodes).

Three measurable invariants we test (declared BEFORE implementing):

  1. With β high (e.g. 16), attention concentrates on the single
     most-similar pattern (max weight > 0.5 for clearly-matching cue).

  2. With β low (e.g. 0.5), attention spreads near-uniformly across
     the K stored patterns (no single weight dominates).

  3. Pattern completion from a partial cue (encode only task_text)
     surfaces the episode whose full summary embedding is closest —
     even if other features (final_answer, outcome) differ.
"""
from __future__ import annotations

import time

import numpy as np
import pytest

from verimem.episode import Episode, Trace
from verimem.memory import EpisodicMemory


def _ep(*, id_: str, task_text: str, final_answer: str = "ok") -> Episode:
    return Episode(
        id=id_, task_id="t", task_text=task_text,
        outcome="success", final_answer=final_answer,
        traces=[Trace(
            step=1, thought="x", action="x", action_input="{}",
            observation="x",
        )],
    )


# ---------- Test 1: high β concentrates attention -----------------------


def test_high_beta_concentrates_on_closest_pattern(tmp_path):
    from verimem import embedding as emb_mod
    from verimem.hopfield import hopfield_complete

    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    mem.store(_ep(id_="exact_match", task_text="fix calc.py arithmetic bug"))
    mem.store(_ep(id_="loose_match", task_text="deploy frontend production"))
    mem.store(_ep(id_="far_match", task_text="renew SSL certificate"))

    cue = emb_mod.encode("fix calc.py arithmetic bug")
    completed, weights, ids = hopfield_complete(mem, cue, beta=16.0)

    # The attention should concentrate on `exact_match`.
    weight_by_id = dict(zip(ids, weights, strict=True))
    assert weight_by_id["exact_match"] > 0.5, (
        f"β=16 should concentrate; got weights {weight_by_id}"
    )
    assert weight_by_id["exact_match"] > weight_by_id["loose_match"]


# ---------- Test 2: low β spreads attention -----------------------------


def test_low_beta_spreads_attention(tmp_path):
    from verimem import embedding as emb_mod
    from verimem.hopfield import hopfield_complete

    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    for i in range(5):
        mem.store(_ep(id_=f"sim_{i}", task_text=f"fix bug variant {i}"))

    cue = emb_mod.encode("fix bug")
    _completed, weights, _ids = hopfield_complete(mem, cue, beta=0.5)

    # No single weight should dominate.
    assert max(weights) < 0.5, (
        f"β=0.5 should spread attention; max weight {max(weights):.3f}"
    )
    # Weights are a probability distribution
    assert pytest.approx(1.0, abs=1e-5) == sum(weights)


# ---------- Test 3: partial cue completes the full pattern --------------


def test_partial_cue_completes_to_correct_episode(tmp_path):
    """Encode ONLY the task_text as cue, but each episode also has
    a different final_answer (so summary embedding differs). The
    returned attention should still concentrate on the matching
    episode — pattern completion from a partial feature."""
    from verimem import embedding as emb_mod
    from verimem.hopfield import hopfield_complete

    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    mem.store(_ep(
        id_="db_migration",
        task_text="migrate users table to new schema",
        final_answer="executed alembic upgrade head, 47 rows affected",
    ))
    mem.store(_ep(
        id_="frontend",
        task_text="add dark mode toggle to settings page",
        final_answer="merged PR #142, css variables propagated",
    ))
    # Cue = just task_text (no final_answer, no outcome)
    cue = emb_mod.encode("migrate users table to new schema")
    _completed, weights, ids = hopfield_complete(mem, cue, beta=12.0)

    weight_by_id = dict(zip(ids, weights, strict=True))
    assert weight_by_id["db_migration"] > weight_by_id["frontend"]
    assert weight_by_id["db_migration"] > 0.6


# ---------- Test 4: empty memory returns degenerate ---------------------


def test_empty_memory_returns_empty(tmp_path):
    import numpy as np

    from verimem.hopfield import hopfield_complete

    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    cue = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    completed, weights, ids = hopfield_complete(mem, cue, beta=8.0)
    assert ids == []
    assert weights.size == 0
    assert completed.size == 0


# ---------- Test 5: determinism ------------------------------------------


def test_determinism(tmp_path):
    from verimem import embedding as emb_mod
    from verimem.hopfield import hopfield_complete

    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    for i in range(4):
        mem.store(_ep(id_=f"e{i}", task_text=f"task {i}"))

    cue = emb_mod.encode("task 1")
    a, w_a, ids_a = hopfield_complete(mem, cue, beta=8.0)
    b, w_b, ids_b = hopfield_complete(mem, cue, beta=8.0)
    assert ids_a == ids_b
    assert np.allclose(a, b)
    assert np.allclose(w_a, w_b)


# ---------- Test 6: high β behaves like argmax (consistency) ------------


def test_argmax_equivalence_at_very_high_beta(tmp_path):
    """As β → ∞, softmax → argmax. Test that with β=64, the attention
    weights match a hard one-hot over the cosine-argmax pattern."""
    from verimem import embedding as emb_mod
    from verimem.hopfield import hopfield_complete

    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    mem.store(_ep(id_="winner", task_text="fix arithmetic in calc.py module"))
    mem.store(_ep(id_="loser_a", task_text="something different about networking"))
    mem.store(_ep(id_="loser_b", task_text="another off-topic SSL renewal"))

    cue = emb_mod.encode("fix arithmetic in calc.py module")
    _comp, weights, ids = hopfield_complete(mem, cue, beta=64.0)

    weight_by_id = dict(zip(ids, weights, strict=True))
    assert weight_by_id["winner"] > 0.95
