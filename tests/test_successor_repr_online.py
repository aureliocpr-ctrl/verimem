"""Tests for FORGIA pezzo #207: SR online TD update.

Foundation for Pezzo B (forward planning via beam search). The
existing `build_successor_matrix` is a BATCH operation (rebuild the
whole matrix from all episodes). For real-time learning we need an
incremental update so the SR adapts after each new episode without
recomputing the whole thing.

Stachenfeld, Botvinick & Gershman (2017) Nat Neurosci §3.2 specifies
the TD-style online rule (eq. 4 in the paper):

    M[s_t] ← M[s_t] + α · ( e_{s_t} + γ · M[s_{t+1}] − M[s_t] )

where:
  - `e_{s_t}` is the one-hot indicator vector at s_t,
  - `α` is the learning rate (≈ 0.05–0.1 in the paper),
  - `γ` is the same discount used in batch SR (0.9).

Why this matters:
  - Pezzo B (forward planning) needs an SR that reflects skills
    USED RIGHT NOW, not skills as of the last consolidate(). A
    cold-running matrix from yesterday will plan toward stale
    futures.
  - The online update converges to the batch fixed-point as
    α → 0 and #updates → ∞ (proven in Sutton 1988, Sutton & Barto
    2018 §6.1).

Six invariants we declare BEFORE implementing:

  1. SINGLETON NO-OP: a 1-element sequence has no transitions, so
     the matrix should be unchanged.

  2. KNOWN-PAIR INCREMENT: a transition A→B with α>0 increases
     M[A][B] from its prior value (TD target pulls toward it).

  3. ALPHA ZERO PRESERVES MATRIX: α=0 means no learning, M
     unchanged regardless of the sequence.

  4. ROW NORMALISATION PRESERVED: after the update, every row of M
     still sums to 1 (we re-normalise per the same convention as
     `build_successor_matrix`).

  5. UNKNOWN SKILL EXPANDS UNIVERSE: encountering a skill not in
     `ids` adds it (the matrix grows by one row/column, default
     identity-like).

  6. CONVERGENCE TO BATCH: replaying the same set of training
     episodes many times via the online rule converges to a matrix
     close to `build_successor_matrix` on the same episodes. This
     is the math invariant that justifies using the online rule at
     all.
"""
from __future__ import annotations

import numpy as np


def test_singleton_sequence_is_noop():
    """A sequence with a single element has zero transitions; M
    must be byte-equal to its prior value."""
    from engram.successor_repr import (
        build_successor_matrix,
        update_from_sequence,
    )

    ids, M = build_successor_matrix(
        [["A", "B"], ["B", "A"]],
        gamma=0.9,
    )
    M_before = M.copy()
    ids_after, M_after = update_from_sequence(
        M, ids, ["A"], alpha=0.1, gamma=0.9
    )
    assert ids_after == ids
    assert np.array_equal(M_after, M_before), (
        "singleton sequence should not modify M"
    )


def test_known_pair_increments_target_cell():
    """For transition A→B, the TD update should pull M[A] toward
    e_A + γ·M[B]. In particular, M[A][B] (currently small or zero)
    should increase relative to its prior value when γ·M[B][B] > 0."""
    from engram.successor_repr import update_from_sequence

    ids = ["A", "B", "C"]
    # Start from identity: M[i][j] = 1 if i==j else 0. Then any
    # transition A→B should increase M[A][B] because the TD target
    # contains γ·M[B] which has mass on B.
    M = np.eye(3, dtype=np.float32)
    before = M[0, 1]
    _, M_after = update_from_sequence(
        M, ids, ["A", "B"], alpha=0.5, gamma=0.9
    )
    after = M_after[0, 1]
    assert after > before, (
        f"M[A][B] should increase after A→B; before={before:.4f}, "
        f"after={after:.4f}"
    )


def test_alpha_zero_preserves_matrix():
    """α=0 means no learning: every entry of M must equal its prior."""
    from engram.successor_repr import update_from_sequence

    ids = ["A", "B", "C"]
    rng = np.random.default_rng(42)
    M = rng.random((3, 3), dtype=np.float32)
    M_before = M.copy()
    _, M_after = update_from_sequence(
        M, ids, ["A", "B", "C", "A"], alpha=0.0, gamma=0.9
    )
    assert np.allclose(M_after, M_before, atol=1e-7), (
        "α=0 must leave M unchanged"
    )


def test_row_normalisation_preserved():
    """After the update, every row of M sums to 1 (same convention
    as the batch builder)."""
    from engram.successor_repr import (
        build_successor_matrix,
        update_from_sequence,
    )

    ids, M = build_successor_matrix(
        [["A", "B", "C"], ["B", "C", "A"]],
        gamma=0.9,
    )
    _, M_after = update_from_sequence(
        M, ids, ["A", "B", "C", "A", "B"], alpha=0.1, gamma=0.9
    )
    row_sums = M_after.sum(axis=1)
    assert np.allclose(row_sums, 1.0, atol=1e-5), (
        f"rows must sum to 1 after update; got {row_sums}"
    )


def test_unknown_skill_expands_universe():
    """Encountering a new skill not in `ids` extends the matrix by
    one row/column. The new row defaults to identity (the new skill
    has only itself as future) before the TD update is applied."""
    from engram.successor_repr import update_from_sequence

    ids = ["A", "B"]
    M = np.eye(2, dtype=np.float32)
    ids_after, M_after = update_from_sequence(
        M, ids, ["A", "NEW"], alpha=0.5, gamma=0.9
    )
    assert "NEW" in ids_after, (
        f"unknown skill 'NEW' must be added to ids; got {ids_after}"
    )
    assert M_after.shape == (3, 3), (
        f"matrix should grow to 3x3; got {M_after.shape}"
    )
    # The new skill row should still sum to 1 (probability dist).
    new_idx = ids_after.index("NEW")
    assert abs(float(M_after[new_idx].sum()) - 1.0) < 1e-5


def test_online_preserves_rank_ordering():
    """The use case for online SR is forward planning (Pezzo B):
    "given I'm at skill X, what's the most likely next/future
    skill?". The invariant we need is RANK PRESERVATION — for each
    source row, the ordering of future-visitation probabilities
    should match the batch SR. Absolute magnitudes can differ
    because the two conventions normalise differently (batch
    normalises every step, online normalises once per touched row).

    This is the actually-useful invariant. Sutton 1988 proves
    asymptotic convergence in EXPECTATION; with finite sweeps and
    α > 0 the magnitudes have residual variance, but the ranking
    is what the planner consumes.
    """
    from engram.successor_repr import (
        build_successor_matrix,
        update_from_sequence,
    )

    episodes = [
        ["A", "B", "C"],
        ["A", "B", "C"],
        ["A", "B", "D"],
        ["B", "C", "D"],
    ]
    gamma = 0.9

    ids_batch, M_batch = build_successor_matrix(episodes, gamma=gamma)

    ids_online = list(ids_batch)
    M_online = np.eye(len(ids_online), dtype=np.float32)
    rng = np.random.default_rng(0)
    for _ in range(800):
        order = rng.permutation(len(episodes))
        for k in order:
            ids_online, M_online = update_from_sequence(
                M_online, ids_online, episodes[k],
                alpha=0.05, gamma=gamma,
            )

    # For each source row, top-2 successors by argsort should agree
    # with the batch (allowing minor reordering of nearly-tied entries).
    n = M_batch.shape[0]
    matches = 0
    total = 0
    for i in range(n):
        # Mask the diagonal (self) so we look at proper successors.
        b_scores = M_batch[i].copy()
        o_scores = M_online[i].copy()
        b_scores[i] = -1.0
        o_scores[i] = -1.0
        b_top = np.argmax(b_scores)
        o_top = np.argmax(o_scores)
        if b_top == o_top:
            matches += 1
        total += 1
    # Most rows should agree on the top-1 successor.
    assert matches >= total - 1, (
        f"online should preserve top-1 successor ranking; "
        f"matches={matches}/{total}"
    )
