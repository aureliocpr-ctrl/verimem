"""Successor Representation (Dayan 1993, Stachenfeld et al. 2017).

Paper:
  - Dayan (1993) "Improving generalisation for temporal difference
    learning: The successor representation", Neural Computation
    5(4):613–624.
  - Stachenfeld, Botvinick & Gershman (2017) "The hippocampus as a
    predictive map", Nat Neurosci 20:1643–1653, doi 10.1038/nn.4650.

Idea: instead of storing transitions only, the brain caches
*expected discounted future visitations* of each state from each
state. A "place cell" doesn't fire just for the current location —
it fires for places you're likely to visit soon. This is the
Successor Representation:

    M[i][j] = E[ Σ_t γ^t · 1{s_t = j} | s_0 = i ]

Closed form:

    M = (I - γ · P)^(-1)

where P is the empirical transition probability matrix from the
agent's episodes. With γ ∈ [0, 1) the matrix exists and is unique.

Iterative form (numerically robust for sparse P, also matches the
biological learning dynamics):

    M_{k+1} = (1 - γ) · I + γ · P · M_k

We row-normalise M so each row is a discounted distribution over
future skills (summing to 1).

For HippoAgent:
  - Predict the next skill given the current one (planning).
  - Cluster skills by similar future trajectories ("you go to
    similar places").
  - Provide a smarter "what-comes-next" prior than the bare
    transition matrix (which is one-step only).

Cost: building P is O(N·k) where N=episodes, k=avg trajectory length.
The matrix inverse / 50-step iteration is O(S³) where S=#unique skills.
For S ≤ 1000 this is sub-second.
"""
from __future__ import annotations

import math
from collections.abc import Callable, Sequence

import numpy as np


def _collect_skills(episodes: Sequence[Sequence[str]]) -> list[str]:
    """Stable-sorted list of unique skill ids across all episodes.
    Sorting keeps the matrix index reproducible across runs."""
    seen: set[str] = set()
    for ep in episodes:
        seen.update(ep)
    return sorted(seen)


def build_transition_matrix(
    episodes: Sequence[Sequence[str]],
) -> tuple[list[str], np.ndarray]:
    """Empirical transition matrix P[i][j] = P(s_{t+1}=j | s_t=i).

    Counts pair-wise transitions across each episode's skill sequence,
    then row-normalises. Sink states (skills that appear only as the
    last step of an episode) get a self-loop so the row remains a
    valid distribution (no divide-by-zero downstream).
    """
    ids = _collect_skills(episodes)
    if not ids:
        return [], np.zeros((0, 0), dtype=np.float32)
    n = len(ids)
    idx = {sid: i for i, sid in enumerate(ids)}
    counts = np.zeros((n, n), dtype=np.float32)
    for ep in episodes:
        for a, b in zip(ep, ep[1:], strict=False):
            counts[idx[a], idx[b]] += 1.0
    # Row-normalise. Rows with zero outgoing transitions become self-loops.
    row_sums = counts.sum(axis=1, keepdims=True)
    zero_rows = row_sums.flatten() == 0.0
    counts[zero_rows] = 0.0
    counts[zero_rows, np.where(zero_rows)[0]] = 1.0  # self-loop on sinks
    row_sums = counts.sum(axis=1, keepdims=True)
    return ids, (counts / row_sums).astype(np.float32)


def build_successor_matrix(
    episodes: Sequence[Sequence[str]],
    *,
    gamma: float = 0.9,
    n_iter: int = 50,
    tol: float = 1e-7,
) -> tuple[list[str], np.ndarray]:
    """Iteratively compute the row-normalised successor matrix.

    Args:
      - `episodes`: list of skill-sequences (one per episode).
      - `gamma`: discount factor; 0 = no future, 0.99 = far horizon.
        Defaults to 0.9 — the value Stachenfeld 2017 reports as a
        good fit for hippocampal place-field profiles.
      - `n_iter`: cap on iterations. Convergence usually < 30 for
        well-behaved P; the cap stops runaway.
      - `tol`: early-exit when ‖M_{k+1} - M_k‖_∞ < tol.

    Returns: `(ids, M)` where `ids` is the sorted skill-ID list and
    `M` is a (S, S) row-stochastic matrix.
    """
    if not (0.0 <= gamma < 1.0):
        raise ValueError(f"gamma must be in [0, 1); got {gamma}")
    ids, P = build_transition_matrix(episodes)
    n = P.shape[0]
    if n == 0:
        return [], np.zeros((0, 0), dtype=np.float32)
    eye = np.eye(n, dtype=np.float32)
    if gamma == 0.0:
        # Degenerate case: no future, just the current state.
        return ids, eye
    M = eye.copy()
    for _ in range(n_iter):
        M_next = (1.0 - gamma) * eye + gamma * (P @ M)
        # Row-normalise each step so the result stays a distribution.
        row_sums = M_next.sum(axis=1, keepdims=True)
        row_sums[row_sums < 1e-12] = 1.0
        M_next = M_next / row_sums
        if float(np.max(np.abs(M_next - M))) < tol:
            return ids, M_next.astype(np.float32)
        M = M_next
    return ids, M.astype(np.float32)


def predict_next(
    current_skill: str,
    ids: list[str],
    matrix: np.ndarray,
    *,
    top_k: int = 1,
) -> list[str]:
    """Top-k most-likely next skills given the current one.

    `matrix` should be a one-step transition matrix `P` (the output of
    `build_transition_matrix`). Passing the full successor matrix `M`
    would mix in long-horizon visitations dominated by absorbing
    sinks — not what "next" means.

    The current skill is masked from the result (no self-loop).
    Returns [] if `current_skill` is unknown.
    """
    if current_skill not in ids:
        return []
    i = ids.index(current_skill)
    scores = matrix[i].copy()
    scores[i] = -1.0  # mask self
    if top_k >= len(ids):
        order = np.argsort(-scores)
    else:
        # argpartition for efficiency with large skill libraries.
        top = np.argpartition(-scores, top_k)[:top_k]
        order = top[np.argsort(-scores[top])]
    return [ids[j] for j in order if scores[j] >= 0.0]


def update_from_sequence(
    M: np.ndarray,
    ids: list[str],
    sequence: Sequence[str],
    *,
    alpha: float = 0.05,
    gamma: float = 0.9,
) -> tuple[list[str], np.ndarray]:
    """Online TD-style update of the successor matrix from a single
    skill sequence. Foundation for forward planning (Pezzo B).

    Stachenfeld, Botvinick & Gershman (2017) Nat Neurosci §3.2 eq. 4:

        M[s_t] ← M[s_t] + α · ( e_{s_t} + γ · M[s_{t+1}] − M[s_t] )

    where `e_{s_t}` is the one-hot vector at s_t. The rule is the
    same TD(0) update Sutton (1988) proves convergent in expectation
    to the batch fixed-point M = (I − γP)^(−1) (Sutton & Barto 2018
    §6.1). Convergence holds for α ∈ (0, 1] with α small (≤ 0.1) for
    low residual variance.

    Args:
      - `M`: prior successor matrix, shape (S, S). Mutated copy is
        returned; the input is left untouched.
      - `ids`: skill-id list aligned with `M` rows/columns.
      - `sequence`: ordered skills observed in one episode/run.
      - `alpha`: learning rate. 0.05 (paper default) gives stable
        slow learning; 0.1 is tolerable for ≤ 1e3 updates. α=0 is a
        no-op (returns a fresh copy).
      - `gamma`: discount factor; must match the batch SR's γ
        otherwise the online and batch matrices represent different
        horizons.

    Behaviour:
      - Sequences shorter than 2 are no-ops (no transitions).
      - Skills not in `ids` are appended; the matrix grows by one
        row/column with a self-loop default (so the new row is a
        valid distribution before any TD pull).
      - Only rows that received a TD update are re-normalised, so
        passing a non-normalised prior with α=0 returns the prior
        verbatim (useful as a safety guarantee).

    Returns: `(ids_after, M_after)`. `ids_after` is `ids` plus any
    newly seen skills appended in first-seen order. `M_after` is a
    fresh array — `M` is not mutated.
    """
    if not (0.0 <= alpha <= 1.0):
        raise ValueError(f"alpha must be in [0, 1]; got {alpha}")
    if not (0.0 <= gamma < 1.0):
        raise ValueError(f"gamma must be in [0, 1); got {gamma}")

    # Early-out: α=0 → no learning, no normalisation. Singleton/empty
    # sequence has no transitions to apply.
    if alpha == 0.0 or len(sequence) < 2:
        return list(ids), M.copy()

    ids_list = list(ids)
    M_new = M.copy().astype(np.float32)
    idx: dict[str, int] = {sid: i for i, sid in enumerate(ids_list)}

    # Expand the matrix for any never-seen skill, preserving first-
    # seen order. New rows start as a self-loop (one-hot on self) so
    # they're a valid 1-summing distribution before any TD update.
    seen_new: list[str] = []
    for s in sequence:
        if s not in idx and s not in seen_new:
            seen_new.append(s)
    for s in seen_new:
        ids_list.append(s)
        idx[s] = len(ids_list) - 1
        n_old = M_new.shape[0]
        # Pad with a zero column.
        M_new = np.hstack(
            [M_new, np.zeros((n_old, 1), dtype=np.float32)]
        )
        # Pad with a self-loop row.
        new_row = np.zeros((1, n_old + 1), dtype=np.float32)
        new_row[0, n_old] = 1.0
        M_new = np.vstack([M_new, new_row])

    # TD(0) sweep across the transitions in `sequence`.
    n = M_new.shape[0]
    touched: set[int] = set()
    for s_t, s_next in zip(sequence, sequence[1:], strict=False):
        i = idx[s_t]
        j = idx[s_next]
        e = np.zeros(n, dtype=np.float32)
        e[i] = 1.0
        target = e + gamma * M_new[j]
        M_new[i] = M_new[i] + alpha * (target - M_new[i])
        touched.add(i)

    # Re-normalise ONLY the rows we modified; untouched rows keep
    # whatever convention the caller's prior had.
    for i in touched:
        row_sum = float(M_new[i].sum())
        if row_sum > 1e-12:
            M_new[i] = M_new[i] / row_sum

    return ids_list, M_new.astype(np.float32)


def forward_plan(
    start_skill: str,
    ids: list[str],
    P: np.ndarray,
    *,
    depth: int = 3,
    beam_width: int = 3,
    goal: Callable[[list[str]], bool] | None = None,
) -> list[tuple[list[str], float]]:
    """Forward planning via beam search on the transition matrix.

    Pfeiffer & Foster (2013) Nature 497:74–79 — "Hippocampal place-
    cell sequences depict future paths to remembered goals". Place
    cells fire forward sweeps from current location toward the goal
    during pause/decision moments, before the body moves. This
    function implements that — multiplicative beam search composing
    one-step transition probabilities along candidate trajectories.

    Why P (one-step) and not M (long-horizon SR)?
      - P[i,j] is a calibrated one-step probability that composes
        multiplicatively along a trajectory, so we get a well-formed
        log-likelihood for each path.
      - M[i,j] is *expected discounted future visitation* — useful
        as a value/heuristic, not as a step probability. Composing
        M values along a path double-counts long-horizon mass.

    Args:
      - `start_skill`: skill id to start the forward sweep from.
      - `ids`: skill-id list aligned with `P` rows/columns.
      - `P`: row-stochastic transition matrix (output of
        `build_transition_matrix`).
      - `depth`: max forward steps. `depth=3` → paths of length up
        to 4 (start + 3 transitions).
      - `beam_width`: max active beams kept per step. Goal-frozen
        paths accumulate beyond this cap.
      - `goal`: optional predicate `path -> bool`. When True for a
        path, that path is frozen (returned as-is, not expanded
        further). Use it to plan toward a target skill or to stop
        when a state predicate is satisfied.

    Returns: list of `(path, log_prob)` tuples sorted by descending
    log-probability. `path` is a list of skill ids, `log_prob` is
    the cumulative natural-log probability of all transitions in
    the path. Returns `[]` if `start_skill ∉ ids`.

    Edge cases:
      - `depth=0`: returns `[([start_skill], 0.0)]`.
      - Zero-probability transitions are pruned (no `log(0)` blowup).
      - Sink states naturally end exploration when their out-edges
        are all self-loops with no further structure.
    """
    if start_skill not in ids:
        return []
    if depth < 0:
        raise ValueError(f"depth must be >= 0; got {depth}")
    if beam_width < 1:
        raise ValueError(f"beam_width must be >= 1; got {beam_width}")

    idx = {sid: i for i, sid in enumerate(ids)}

    if depth == 0:
        return [([start_skill], 0.0)]

    beam: list[tuple[list[str], float]] = [([start_skill], 0.0)]
    frozen: list[tuple[list[str], float]] = []

    for _ in range(depth):
        new_beam: list[tuple[list[str], float]] = []
        for path, lp in beam:
            # Goal hit → freeze and skip expansion.
            if goal is not None and goal(path):
                frozen.append((path, lp))
                continue
            i = idx[path[-1]]
            row = P[i]
            # Vectorised: pick non-zero successors, compose log-prob.
            nz = np.flatnonzero(row > 0.0)
            for j in nz:
                p = float(row[j])
                new_beam.append((path + [ids[int(j)]], lp + math.log(p)))
        # Top beam_width by log-prob (descending).
        new_beam.sort(key=lambda x: -x[1])
        beam = new_beam[:beam_width]
        if not beam:
            break

    # Final goal sweep — paths that hit goal on the last step.
    if goal is not None:
        keep: list[tuple[list[str], float]] = []
        for path, lp in beam:
            if goal(path):
                frozen.append((path, lp))
            else:
                keep.append((path, lp))
        beam = keep

    results = frozen + beam
    results.sort(key=lambda x: -x[1])
    return results


def cluster_by_sr_similarity(
    ids: list[str],
    M: np.ndarray,
    *,
    threshold: float = 0.7,
) -> list[list[str]]:
    """Greedy clustering of skills by cosine on their SR rows.

    Two skills end up in the same cluster when the cosine of their
    rows in the successor matrix is ≥ `threshold`. The metric
    captures "skills that lead to similar future state distributions"
    — orthogonal to semantic-embedding similarity.

    Useful for:
      - Identifying functionally-equivalent skills (different name,
        same purpose).
      - Schema synthesis: skills with the same SR-cluster could be
        consolidated under a meta-skill.

    Args:
      - `ids`: skill id list (from `build_successor_matrix`).
      - `M`: successor matrix (S, S), already row-normalised.
      - `threshold`: cosine cutoff. Default 0.7 — moderately strict;
        relax to 0.5 for fuzzier clustering.

    Returns: list of clusters, each a list of skill ids. Singletons
    appear as 1-element lists. Order within a cluster is by first-
    encountered.
    """
    n = len(ids)
    if n == 0 or M.shape[0] == 0:
        return []
    # Row-normalise to unit-norm so dot product = cosine.
    norms = np.linalg.norm(M, axis=1, keepdims=True)
    norms[norms < 1e-12] = 1.0
    M_unit = M / norms
    sims = M_unit @ M_unit.T

    unvisited = np.ones(n, dtype=bool)
    clusters: list[list[str]] = []
    for i in range(n):
        if not unvisited[i]:
            continue
        # Members: skills with cosine ≥ threshold to skill i, AND
        # still unvisited.
        mask = unvisited & (sims[i] >= threshold)
        members = [ids[j] for j in np.where(mask)[0]]
        clusters.append(members)
        unvisited[mask] = False
    return clusters


__all__ = [
    "build_transition_matrix",
    "build_successor_matrix",
    "predict_next",
    "cluster_by_sr_similarity",
    "update_from_sequence",
    "forward_plan",
]
