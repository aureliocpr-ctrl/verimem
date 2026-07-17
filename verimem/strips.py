"""STRIPS-style forward planner over the skill library.

FORGIA pezzo #209 — Pezzo A. The third leg of "ragionare su task
nuovi": symbolic chaining via preconditions/postconditions.

Background:
  - Anderson (1983, 1996) ACT-R: procedural memory consists of
    production rules `IF <preconditions> THEN <postconditions>`.
  - Fikes & Nilsson (1971) STRIPS: forward search by matching pre
    against current state, applying post on success.
  - Bridges from SR (Pezzo B — statistical correlation, "what tends
    to follow") to symbolic chaining ("what makes this skill
    APPLICABLE right now and what does it ESTABLISH").

The planner is intentionally minimal:
  - State is a `set[str]` of currently-true predicates.
  - A skill is APPLICABLE when `set(skill.preconditions) ⊆ state`.
  - Application produces `state ∪ set(skill.postconditions)`.
  - We use BFS (uniform cost) so the first plan found is the
    shortest in terms of skill count. STRIPS doesn't model `delete`
    lists — once a predicate is true, it stays true. This matches
    "skill effects accumulate" semantics; explicit retraction can
    be added later if real failures need it.

Why not A*? With ≤ 1000 skills and depth ≤ 5, BFS exhausts the
relevant state space in milliseconds and is trivially correct. A*
would need an admissible heuristic, which we don't have without
extra work (Pezzo C structural analogy could supply one).

Cost: O(|skills| × |reachable_states| × max_depth). For 100 skills
and depth 5, that's < 10⁵ state expansions, microseconds total.
"""
from __future__ import annotations

from collections import deque
from collections.abc import Iterable

from .skill import Skill


def plan_strips(
    initial_state: Iterable[str],
    goal_state: Iterable[str],
    skills: list[Skill],
    *,
    max_depth: int = 5,
) -> list[Skill] | None:
    """Forward BFS STRIPS planner.

    Args:
      - `initial_state`: iterable of predicates (strings) currently
        true. Order is irrelevant; sets are used internally.
      - `goal_state`: iterable of predicates that must be true at
        the end of the plan. The plan terminates the moment EVERY
        predicate in `goal_state` is in the current state (so a
        plan that establishes more than the goal is OK — extras
        are harmless).
      - `skills`: candidate operators. Skills with empty `preconditions`
        are always applicable; skills with empty `postconditions`
        are no-ops (they never expand the state and are pruned).
      - `max_depth`: plan-length budget. BFS finds the shortest
        plan first, so this is mostly a safety cap. Defaults to 5
        — long enough for most realistic chains, short enough to
        keep the search bounded.

    Returns: the shortest plan (list of skills, in order to apply)
    or `None` when no plan ≤ `max_depth` exists.

    Edge cases:
      - Goal already satisfied → empty list `[]` (a valid no-op
        plan). Distinct from `None` (impossible).
      - No skills → empty list if goal already satisfied, else None.
      - max_depth=0 → only checks if the initial state satisfies
        the goal; never applies any skill.
    """
    init = set(initial_state)
    goal = set(goal_state)

    # Trivial: goal already met.
    if goal.issubset(init):
        return []

    # BFS: each frontier element is (state_frozenset, plan_so_far).
    # We use frozenset as the visited key to dedupe equivalent
    # states (path-independence: STRIPS without delete-effects is
    # monotone in state, so the same state via different paths is
    # never worth re-exploring).
    queue: deque[tuple[frozenset[str], list[Skill]]] = deque()
    queue.append((frozenset(init), []))
    visited: set[frozenset[str]] = {frozenset(init)}

    while queue:
        state, plan = queue.popleft()
        if len(plan) >= max_depth:
            continue
        for sk in skills:
            pre = set(sk.preconditions or [])
            if not pre.issubset(state):
                continue
            post = set(sk.postconditions or [])
            if not post:
                # No-op skill: applying it changes nothing. Prune.
                continue
            new_state = state | post
            if new_state == state:
                # All effects already true → prune (would loop).
                continue
            new_state_fs = frozenset(new_state)
            if new_state_fs in visited:
                continue
            visited.add(new_state_fs)
            new_plan = plan + [sk]
            if goal.issubset(new_state):
                return new_plan
            queue.append((new_state_fs, new_plan))
    return None


__all__ = ["plan_strips"]
