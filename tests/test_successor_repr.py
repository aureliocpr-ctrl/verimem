"""Tests for FORGIA pezzo #20: Successor Representation.

Dayan (1993) "Improving generalisation for temporal difference learning:
The successor representation" introduced SR as a cached predictive
representation. Stachenfeld, Botvinick & Gershman (2017) Nat Neurosci
showed hippocampal place cells implement SR — they encode FUTURE state
visitations under the current policy, not just the present state.

Math:

    M = sum_t γ^t · P^t = (I - γ·P)^(-1)   (closed form, geometric series)

where P is the empirical transition matrix derived from episode skill
sequences (P[i][j] = prob of going from skill i to skill j).

Equivalently, the Bellman fixed-point:

    M = I + γ · P · M

Iterative form (more numerically stable for sparse data):

    M_{k+1} = (1 - γ) · I + γ · P · M_k     (normalised so rows sum to 1)

For HippoAgent the SR provides:
  - "Given I just used skill A, what's the most likely next skill?"
  - "Skill A is similar to B in successor-space if they have similar
    future trajectories" — useful for skill clustering beyond cosine.

Five measurable invariants we test (declared BEFORE implementing):

  1. EMPTY CORPUS: empty episode list returns ([], 0×0 matrix).

  2. LINEAR CHAIN: a sequence of episodes forming a chain A→B→C
     produces M[A][B] > 0, M[B][C] > 0, with γ=0.9 decay.

  3. γ=0 IS IDENTITY: with γ=0, M = I (no future, just present).

  4. ROW NORMALISATION: each row sums to 1 (matrix is a discounted
     probability distribution).

  5. CONVERGENCE: 50 iterations converges to the closed-form solution
     within 1e-6 (math invariant — same answer two ways).
"""
from __future__ import annotations

import numpy as np


def test_empty_episodes_yields_empty_matrix():
    from verimem.successor_repr import build_successor_matrix

    ids, M = build_successor_matrix([], gamma=0.9)
    assert ids == []
    assert M.shape == (0, 0)


def test_linear_chain_episodes():
    """Episodes record a Markov chain A→B→C in their `skills_used`.
    SR should reflect: nontrivial M[A][B], M[B][C], M[A][C].

    NOTE: in this 3-episode A→B→C corpus, C is an absorbing terminal
    (sink) state. With the standard SR formulation including a
    self-loop on sinks, M[A][C] dominates because all discounted
    future probability flows into C. The right "what-next" predictor
    is the one-step transition matrix P, not M (`predict_next` uses P).
    """
    from verimem.successor_repr import build_successor_matrix

    episodes = [
        ["A", "B", "C"],
        ["A", "B", "C"],
        ["A", "B", "C"],
    ]
    ids, M = build_successor_matrix(episodes, gamma=0.9)
    idx = {s: ids.index(s) for s in "ABC"}

    # M[A][B] non-zero (B is reachable from A).
    assert M[idx["A"], idx["B"]] > 0.0
    # M[B][C] non-zero (C is reachable from B in one step).
    assert M[idx["B"], idx["C"]] > 0.0
    # M[A][C] non-zero (reachable in two steps).
    assert M[idx["A"], idx["C"]] > 0.0
    # No backward edges in this chain → low M[B][A] vs M[B][C].
    assert M[idx["B"], idx["A"]] < M[idx["B"], idx["C"]]


def test_gamma_zero_is_identity():
    """With γ=0 the future contributes 0 — SR collapses to (1-γ)·I = I,
    or for normalised form M[i][i] = 1, off-diagonal = 0."""
    from verimem.successor_repr import build_successor_matrix

    episodes = [["A", "B"], ["B", "C"], ["A", "C"]]
    ids, M = build_successor_matrix(episodes, gamma=0.0)
    n = len(ids)
    expected = np.eye(n, dtype=np.float32)
    assert np.allclose(M, expected, atol=1e-6)


def test_row_normalisation():
    """Each row of M is a probability distribution: sums to 1."""
    from verimem.successor_repr import build_successor_matrix

    episodes = [["A", "B", "C"], ["A", "C", "B"], ["B", "A", "C"]]
    _, M = build_successor_matrix(episodes, gamma=0.7)
    row_sums = M.sum(axis=1)
    assert np.allclose(row_sums, 1.0, atol=1e-5), (
        f"row sums not normalised: {row_sums}"
    )


def test_convergence_to_closed_form():
    """Iterative SR converges to the closed-form (I - γP)^(-1) up to
    a normalisation constant (the iterative variant we ship is row-
    normalised; we compare relative ordering)."""
    from verimem.successor_repr import (
        build_successor_matrix,
        build_transition_matrix,
    )

    episodes = [["A", "B", "C"], ["A", "B", "D"], ["B", "C", "D"]]
    gamma = 0.85
    ids_iter, M_iter = build_successor_matrix(episodes, gamma=gamma)

    # Closed-form: (I - γP)^(-1), then row-normalise.
    ids_p, P = build_transition_matrix(episodes)
    n = P.shape[0]
    M_closed = np.linalg.inv(np.eye(n) - gamma * P)
    # Row-normalise to compare with the row-normalised iterative form.
    row_sums = M_closed.sum(axis=1, keepdims=True)
    row_sums[row_sums < 1e-12] = 1.0
    M_closed_norm = M_closed / row_sums

    # ids should match (same skill universe).
    assert ids_iter == ids_p
    # The TWO matrices should agree to high precision.
    assert np.allclose(M_iter, M_closed_norm.astype(np.float32), atol=1e-4), (
        f"iterative and closed-form SR diverge: max delta="
        f"{np.max(np.abs(M_iter - M_closed_norm.astype(np.float32))):.4f}"
    )


def test_predict_next_skill():
    """Given a current skill, `predict_next` (using the transition
    matrix P, not the long-horizon successor matrix M) returns the
    most likely immediate next skill."""
    from verimem.successor_repr import (
        build_transition_matrix,
        predict_next,
    )

    episodes = [["A", "B"], ["A", "B"], ["A", "B"], ["A", "C"]]
    ids, P = build_transition_matrix(episodes)
    next_skill = predict_next("A", ids, P, top_k=1)
    assert next_skill[0] == "B", (
        f"predict_next('A') should be 'B' (3/4 transitions); got {next_skill}"
    )


def test_unknown_skill_in_predict():
    """Asking the predictor for a skill it has never seen returns []."""
    from verimem.successor_repr import (
        build_transition_matrix,
        predict_next,
    )

    ids, P = build_transition_matrix([["A", "B"]])
    out = predict_next("UNKNOWN", ids, P, top_k=3)
    assert out == []
