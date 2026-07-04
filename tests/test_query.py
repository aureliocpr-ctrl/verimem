"""FORGIA pezzo #217 — Wave 16: structured query over the skill library.

A pragmatic alternative to a full DSL: explicit kwargs that the
caller composes. Easier to validate (JSON-schema), no parser
needed, and Claude Code's MCP layer maps cleanly to keyword args.

Filters available:
  - status (candidate / promoted / retired)
  - min_trials / max_trials
  - min_fitness / max_fitness (mean)
  - name_contains (case-insensitive substring)
  - has_predicates (True = both pre AND post non-empty,
                    False = at least one empty)
  - has_compiled_macro (skills with fast-path compiled macros)

Sort:
  - sort_by: fitness | trials | recency | name
  - desc: bool

Output: list of skills (already filtered + sorted), capped by
`limit`.

Eight invariants:
  1. No filters → return all (capped).
  2. status filter.
  3. min/max trials filter.
  4. min/max fitness filter.
  5. name_contains case-insensitive.
  6. has_predicates True/False.
  7. sort_by fitness / recency.
  8. limit respected.
"""
from __future__ import annotations

import time

from engram.skill import Skill


def _make_skills() -> list[Skill]:
    now = time.time()
    return [
        Skill(id="alpha", name="alpha_skill", trials=10, successes=8,
              status="promoted", last_used_at=now - 86400 * 1,
              preconditions=["pre_a"], postconditions=["post_a"]),
        Skill(id="beta", name="beta_skill", trials=20, successes=5,
              status="promoted", last_used_at=now - 86400 * 5),
        Skill(id="gamma", name="gamma_skill", trials=2, successes=2,
              status="candidate", last_used_at=now - 86400 * 30,
              preconditions=["pre_g"], postconditions=["post_g"]),
        Skill(id="delta", name="delta_zone", trials=0, successes=0,
              status="candidate", last_used_at=0.0),
        Skill(id="epsilon", name="retired_thing", trials=15, successes=2,
              status="retired", last_used_at=now - 86400 * 100),
    ]


def test_no_filters_returns_all():
    from engram.query import query_skills

    out = query_skills(_make_skills())
    assert len(out) == 5


def test_status_filter():
    from engram.query import query_skills

    out = query_skills(_make_skills(), status="promoted")
    ids = {s.id for s in out}
    assert ids == {"alpha", "beta"}


def test_min_max_trials():
    from engram.query import query_skills

    out = query_skills(_make_skills(), min_trials=5, max_trials=15)
    ids = {s.id for s in out}
    # alpha=10, beta=20 (out), gamma=2 (out), delta=0 (out), epsilon=15
    assert ids == {"alpha", "epsilon"}


def test_min_max_fitness():
    from engram.query import query_skills

    # alpha 8/10 → mean ~0.75, beta 5/20 → 0.27, gamma 2/2 → 0.75,
    # epsilon 2/15 → 0.18, delta 0/0 → 0.5 (prior).
    out = query_skills(_make_skills(), min_fitness=0.5)
    ids = {s.id for s in out}
    assert "alpha" in ids
    assert "gamma" in ids
    assert "delta" in ids  # prior 0.5 is the boundary, inclusive
    assert "beta" not in ids
    assert "epsilon" not in ids


def test_name_contains_case_insensitive():
    from engram.query import query_skills

    out = query_skills(_make_skills(), name_contains="SKILL")
    ids = {s.id for s in out}
    # alpha, beta, gamma all have "_skill" suffix.
    assert ids == {"alpha", "beta", "gamma"}


def test_has_predicates_true():
    from engram.query import query_skills

    out = query_skills(_make_skills(), has_predicates=True)
    ids = {s.id for s in out}
    # alpha and gamma have both pre and post.
    assert ids == {"alpha", "gamma"}


def test_has_predicates_false():
    from engram.query import query_skills

    out = query_skills(_make_skills(), has_predicates=False)
    ids = {s.id for s in out}
    # beta, delta, epsilon have empty pre+post.
    assert "beta" in ids
    assert "delta" in ids
    assert "epsilon" in ids
    # alpha and gamma have both → excluded.
    assert "alpha" not in ids
    assert "gamma" not in ids


def test_sort_by_fitness_desc():
    from engram.query import query_skills

    out = query_skills(_make_skills(), sort_by="fitness", desc=True)
    # First should be highest-fitness skill.
    assert out[0].id in ("alpha", "gamma")  # both ~0.75


def test_sort_by_recency_desc():
    from engram.query import query_skills

    out = query_skills(_make_skills(), sort_by="recency", desc=True)
    # Most-recently-used first.
    assert out[0].id == "alpha"


def test_limit_respected():
    from engram.query import query_skills

    out = query_skills(_make_skills(), limit=2)
    assert len(out) == 2


def test_combined_filters():
    from engram.query import query_skills

    out = query_skills(
        _make_skills(),
        status="promoted",
        min_fitness=0.5,
    )
    ids = {s.id for s in out}
    # promoted + mean ≥ 0.5: alpha (0.75) yes, beta (0.27) no.
    assert ids == {"alpha"}
