"""FORGIA pezzo #213 — Wave 12: auto-derive STRIPS predicates from
episode sequences.

Most existing skills (the 318 in the live library) have empty
preconditions/postconditions because the v1 STRIPS schema is new.
Manually filling them is impractical at scale. But we already have
a rich signal: episode skill sequences encode "X tends to come
before Y" — exactly the structure STRIPS needs.

Heuristic (zero LLM):
  - For target skill Y:
      precondition `after_X` is added IF skill X immediately precedes
      Y in ≥ `threshold` fraction of episodes where Y appears.
  - Postcondition `after_Y` is ALWAYS added (the trivial "I ran Y"
    marker). Composes naturally: skill A's post becomes skill B's
    pre when B regularly follows A.

This is auto-supervised — we leverage the SR data we already have to
seed STRIPS. Once 60-70% of skills have derived pre/post, the STRIPS
planner becomes useful on the real corpus.

Six invariants:

  1. NO EPISODES → empty pre, postconditions = [after_<skill_id>].
  2. SKILL NEVER SEEN → empty pre + post.
  3. CONSISTENT PREDECESSOR: A→B in 100% of B's appearances → B.pre
     contains "after_A".
  4. INCONSISTENT PREDECESSORS: 50/50 split below threshold → no
     precondition added.
  5. FIRST-IN-EPISODE never adds pre (no predecessor).
  6. THRESHOLD RESPECTED: lowering threshold lets weaker patterns
     through.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class _FakeEp:
    skills_used: list[str]


def test_no_episodes_returns_minimal_post_only():
    from engram.predicate_derivation import derive_predicates_from_episodes

    pre, post = derive_predicates_from_episodes(
        "skill_X", episodes=[], threshold=0.5,
    )
    assert pre == []
    # Trivial self-marker post is always present.
    assert post == ["after_skill_X"]


def test_skill_never_seen_in_episodes():
    """Skill not present in any episode: no signal, only trivial post."""
    from engram.predicate_derivation import derive_predicates_from_episodes

    eps = [_FakeEp(["A", "B"]), _FakeEp(["C", "D"])]
    pre, post = derive_predicates_from_episodes(
        "Z", episodes=eps, threshold=0.5,
    )
    assert pre == []
    assert post == ["after_Z"]


def test_consistent_predecessor():
    """A→B in 100% of B's appearances → B has 'after_A' precondition."""
    from engram.predicate_derivation import derive_predicates_from_episodes

    eps = [
        _FakeEp(["A", "B"]),
        _FakeEp(["A", "B", "C"]),
        _FakeEp(["X", "A", "B"]),
    ]
    pre, post = derive_predicates_from_episodes(
        "B", episodes=eps, threshold=0.5,
    )
    assert "after_A" in pre, (
        f"A precedes B 3/3 times; expected 'after_A' in pre; got {pre}"
    )


def test_inconsistent_predecessors_below_threshold():
    """When B is preceded by A 50% and C 50% (each below 0.5 threshold
    when threshold is 0.6), neither becomes a precondition."""
    from engram.predicate_derivation import derive_predicates_from_episodes

    eps = [
        _FakeEp(["A", "B"]),
        _FakeEp(["A", "B"]),
        _FakeEp(["C", "B"]),
        _FakeEp(["C", "B"]),
    ]
    pre, post = derive_predicates_from_episodes(
        "B", episodes=eps, threshold=0.6,
    )
    # Each predecessor only at 0.5, below the 0.6 threshold.
    assert "after_A" not in pre
    assert "after_C" not in pre


def test_first_in_episode_no_predecessor():
    """If B is always first in its episode, no predecessor exists →
    pre stays empty."""
    from engram.predicate_derivation import derive_predicates_from_episodes

    eps = [
        _FakeEp(["B"]),
        _FakeEp(["B", "X"]),
        _FakeEp(["B", "Y"]),
    ]
    pre, post = derive_predicates_from_episodes(
        "B", episodes=eps, threshold=0.5,
    )
    assert pre == []


def test_lower_threshold_admits_weaker_patterns():
    """Threshold 0.3 lets through patterns the 0.7 threshold rejects."""
    from engram.predicate_derivation import derive_predicates_from_episodes

    eps = [
        _FakeEp(["A", "B"]),
        _FakeEp(["A", "B"]),
        _FakeEp(["C", "B"]),
        _FakeEp(["C", "B"]),
        _FakeEp(["C", "B"]),
    ]
    # A precedes B 2/5 = 0.4; C precedes B 3/5 = 0.6.
    pre_loose, _ = derive_predicates_from_episodes(
        "B", episodes=eps, threshold=0.3,
    )
    pre_strict, _ = derive_predicates_from_episodes(
        "B", episodes=eps, threshold=0.7,
    )
    # Loose: both A (0.4) and C (0.6) pass.
    assert "after_A" in pre_loose
    assert "after_C" in pre_loose
    # Strict: only nothing meets 0.7.
    assert pre_strict == []


def test_self_predecessor_excluded():
    """A skill preceding itself (e.g. retry pattern) should not show
    up as its own precondition (would be circular)."""
    from engram.predicate_derivation import derive_predicates_from_episodes

    eps = [
        _FakeEp(["B", "B"]),
        _FakeEp(["B", "B"]),
    ]
    pre, _ = derive_predicates_from_episodes(
        "B", episodes=eps, threshold=0.4,
    )
    assert "after_B" not in pre, (
        f"self-loop excluded as precondition; got {pre}"
    )


def test_returns_predecessors_sorted_for_determinism():
    """Multiple predecessors above threshold returned in stable
    sorted order (so the result is reproducible)."""
    from engram.predicate_derivation import derive_predicates_from_episodes

    eps = [
        _FakeEp(["A", "X"]),
        _FakeEp(["A", "X"]),
        _FakeEp(["B", "X"]),
        _FakeEp(["B", "X"]),
    ]
    pre, _ = derive_predicates_from_episodes(
        "X", episodes=eps, threshold=0.4,
    )
    # Both A (0.5) and B (0.5) pass. Result must be sorted.
    assert pre == sorted(pre)


def test_only_immediate_predecessor_counts():
    """`A → C → B` does NOT make A a predecessor of B (only C is).
    Multi-step ancestry would over-trigger preconditions."""
    from engram.predicate_derivation import derive_predicates_from_episodes

    eps = [
        _FakeEp(["A", "C", "B"]),
        _FakeEp(["A", "C", "B"]),
    ]
    pre, _ = derive_predicates_from_episodes(
        "B", episodes=eps, threshold=0.5,
    )
    # Only C (immediate predecessor) qualifies, not A.
    assert "after_C" in pre
    assert "after_A" not in pre
