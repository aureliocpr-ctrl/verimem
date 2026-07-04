"""Tests for FORGIA pezzo #208: forward planning via beam search.

This is Pezzo B — the second leg of the "ragionare su task nuovi"
roadmap. The brain doesn't just remember what worked; it simulates
forward sequences of actions before committing. Pfeiffer & Foster
(2013) Nature 497:74–79 showed that during pause/decision moments,
hippocampal place cells fire forward sweeps from current location
toward goal — a literal forward planning trajectory.

Computationally we implement this as beam search on the transition
matrix P (one-step probabilities). Why P and not the long-horizon
SR matrix M? Because beam search composes one-step probabilities
multiplicatively along a path — that's exactly what P encodes.
M is for the "future-visitation" heuristic (Pezzo C, structural
analogy) and for the planner's *value* signal, not the *transitions*
themselves.

API contract:

    forward_plan(
        start_skill, ids, P,
        *,
        depth=3,
        beam_width=3,
        goal=None,
    ) -> list[(path, log_prob)]

  - `path`: list of skill ids, [start_skill, ..., final_skill].
  - `log_prob`: cumulative log-probability of the path (additive in
    log-space; multiplicative in probability-space).
  - Results sorted by log_prob descending (most likely first).

Six invariants we declare BEFORE implementing:

  1. UNKNOWN START → []: a skill not in `ids` returns no plans.

  2. DEPTH 0 → SINGLETONS: depth=0 returns just `[(start, 0.0)]`
     (zero log-prob for the trivial path).

  3. BEAM WIDTH RESPECTED: at most `beam_width` paths in the result.

  4. DESCENDING LOG-PROB: results sorted high → low.

  5. PROBABILITIES MULTIPLY: a 2-step path A→B→C has
     log_prob = log P[A,B] + log P[B,C], to floating-point precision.

  6. GOAL STOPS EARLY: a `goal` predicate that fires partway through
     the depth budget terminates that beam at goal-hit (path may be
     shorter than depth+1).
"""
from __future__ import annotations

import math

import numpy as np


def _toy_P_chain():
    """A→B→C deterministic chain plus stochastic A→D side branch.
       P:
              A     B    C    D
         A [  0   0.7  0   0.3 ]
         B [  0   0    1   0   ]
         C [  0   0    1   0   ]   # sink self-loop
         D [  0   0    0   1   ]   # sink self-loop
    """
    ids = ["A", "B", "C", "D"]
    P = np.array(
        [
            [0.0, 0.7, 0.0, 0.3],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ],
        dtype=np.float32,
    )
    return ids, P


def test_unknown_start_returns_empty():
    from engram.successor_repr import forward_plan

    ids, P = _toy_P_chain()
    out = forward_plan("Z", ids, P, depth=2, beam_width=3)
    assert out == []


def test_depth_zero_returns_singleton():
    """depth=0 means no expansion — just the start, log-prob 0."""
    from engram.successor_repr import forward_plan

    ids, P = _toy_P_chain()
    out = forward_plan("A", ids, P, depth=0, beam_width=3)
    assert out == [(["A"], 0.0)]


def test_beam_width_respected():
    """At most beam_width paths returned."""
    from engram.successor_repr import forward_plan

    ids, P = _toy_P_chain()
    out = forward_plan("A", ids, P, depth=2, beam_width=2)
    assert len(out) <= 2


def test_descending_log_prob():
    """Results sorted from most-likely to least-likely path."""
    from engram.successor_repr import forward_plan

    ids, P = _toy_P_chain()
    out = forward_plan("A", ids, P, depth=2, beam_width=4)
    log_probs = [lp for _, lp in out]
    assert log_probs == sorted(log_probs, reverse=True), (
        f"log_probs not descending: {log_probs}"
    )


def test_probabilities_multiply_in_log_space():
    """log_prob(A→B→C) must equal log P[A,B] + log P[B,C]."""
    from engram.successor_repr import forward_plan

    ids, P = _toy_P_chain()
    out = forward_plan("A", ids, P, depth=2, beam_width=4)
    # Find the A→B→C path.
    abc = next((p, lp) for p, lp in out if p == ["A", "B", "C"])
    expected = math.log(0.7) + math.log(1.0)
    assert abs(abc[1] - expected) < 1e-5, (
        f"log-prob composition wrong: got {abc[1]}, expected {expected}"
    )


def test_goal_stops_beam_early():
    """A goal predicate that fires on `B` should yield paths ending
    at B (length 2: [A, B]), not extended further down to C."""
    from engram.successor_repr import forward_plan

    ids, P = _toy_P_chain()
    out = forward_plan(
        "A", ids, P,
        depth=5, beam_width=3,
        goal=lambda path: path[-1] == "B",
    )
    # At least one returned plan should end at B (the goal).
    assert any(p[-1] == "B" and len(p) == 2 for p, _ in out), (
        f"goal=B should produce [A, B] plans; got {[p for p, _ in out]}"
    )


def test_top_path_is_most_likely():
    """In the toy P, A→B (0.7) → C (1.0) is more likely than
    A→D (0.3) → D (1.0). The top result must be A→B→C."""
    from engram.successor_repr import forward_plan

    ids, P = _toy_P_chain()
    out = forward_plan("A", ids, P, depth=2, beam_width=3)
    assert out, "expected at least one plan"
    top_path, _ = out[0]
    assert top_path == ["A", "B", "C"], (
        f"top path should be A→B→C; got {top_path}"
    )


def test_zero_probability_transitions_excluded():
    """A transition with zero probability must not appear in any
    returned path (log(0) is -inf; we skip such expansions)."""
    from engram.successor_repr import forward_plan

    ids, P = _toy_P_chain()
    out = forward_plan("A", ids, P, depth=1, beam_width=4)
    # B (0.7) and D (0.3) are valid; A and C have zero out-prob from A.
    next_skills = {p[1] for p, _ in out if len(p) == 2}
    assert next_skills <= {"B", "D"}, (
        f"unexpected zero-prob transitions: {next_skills}"
    )
