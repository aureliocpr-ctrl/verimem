"""Tests for FORGIA pezzo #209 — Pezzo A: STRIPS pre/post on skills.

Anderson (1983, 1996) ACT-R: procedural memory consists of production
rules of the form `IF <preconditions> THEN <postconditions>`. Fikes &
Nilsson (1971) STRIPS planner: chain such rules forward from initial
state to goal by matching preconditions against the current state and
adding postconditions on success.

For HippoAgent: each skill becomes a STRIPS operator. The planner
chains skills by:
  - Match: skill.preconditions ⊆ current_state
  - Apply: current_state ← current_state ∪ skill.postconditions

This is the bridge from SR (statistical correlation) to STRIPS
(symbolic chaining). With both, the agent can:
  - Plan multi-step trajectories with goal-directed inference
  - Detect when a skill is APPLICABLE (pre satisfied) before trying it
  - Compose new skills from existing ones (post of A = pre of B)

Three groups of invariants:

  GROUP 1 — Skill schema:
    1. Skills default to empty pre/post (back-compat: existing
       skills don't break).
    2. Round-trip JSON serialise/deserialise preserves pre/post.
    3. Loading an old dict (no pre/post keys) defaults to empty.

  GROUP 2 — Forward planner:
    4. Goal already satisfied → empty plan.
    5. Single-skill plan: pre matches initial, post covers goal.
    6. Multi-step chain: skill_a→skill_b → goal.
    7. No applicable skills → None.
    8. Depth budget exhausted → None.
    9. Shortest plan: BFS prefers fewer steps.
"""
from __future__ import annotations

from verimem.skill import Skill

# ---------- GROUP 1: Skill schema ----------------------------------------


def test_skill_has_default_empty_pre_post():
    """Default Skill() has preconditions=[] and postconditions=[]."""
    s = Skill()
    assert s.preconditions == []
    assert s.postconditions == []


def test_skill_pre_post_round_trip_dict():
    """Skill → to_dict → from_dict preserves pre/post."""
    s = Skill(
        id="x",
        name="login",
        preconditions=["have_credentials"],
        postconditions=["authenticated", "session_active"],
    )
    d = s.to_dict()
    assert "preconditions" in d
    assert "postconditions" in d
    s2 = Skill.from_dict(d)
    assert s2.preconditions == ["have_credentials"]
    assert s2.postconditions == ["authenticated", "session_active"]


def test_old_skill_dict_loads_with_default_pre_post():
    """Loading an old skill JSON (no pre/post keys) must not crash;
    fields default to empty lists."""
    legacy = {
        "id": "old1",
        "version": 1,
        "name": "legacy_skill",
        "trigger": "old trigger",
    }
    s = Skill.from_dict(legacy)
    assert s.preconditions == []
    assert s.postconditions == []


# ---------- GROUP 2: STRIPS planner --------------------------------------


def _toy_skills() -> list[Skill]:
    """Toy skill set forming a chain:
       authenticate: pre={have_creds}, post={logged_in}
       fetch_data:   pre={logged_in},   post={data_loaded}
       render_view:  pre={data_loaded}, post={ui_rendered}
       logout:       pre={logged_in},   post={logged_out}
    """
    return [
        Skill(id="auth", name="authenticate",
              preconditions=["have_creds"],
              postconditions=["logged_in"]),
        Skill(id="fetch", name="fetch_data",
              preconditions=["logged_in"],
              postconditions=["data_loaded"]),
        Skill(id="render", name="render_view",
              preconditions=["data_loaded"],
              postconditions=["ui_rendered"]),
        Skill(id="logout", name="logout",
              preconditions=["logged_in"],
              postconditions=["logged_out"]),
    ]


def test_goal_already_satisfied_returns_empty_plan():
    """When initial_state already includes goal, the plan is []."""
    from verimem.strips import plan_strips

    plan = plan_strips(
        initial_state={"already_done"},
        goal_state={"already_done"},
        skills=_toy_skills(),
    )
    assert plan == []


def test_single_skill_plan():
    """One skill bridges initial→goal."""
    from verimem.strips import plan_strips

    plan = plan_strips(
        initial_state={"have_creds"},
        goal_state={"logged_in"},
        skills=_toy_skills(),
    )
    assert plan is not None
    assert [s.id for s in plan] == ["auth"]


def test_multi_step_chain():
    """Plan should chain auth → fetch → render."""
    from verimem.strips import plan_strips

    plan = plan_strips(
        initial_state={"have_creds"},
        goal_state={"ui_rendered"},
        skills=_toy_skills(),
    )
    assert plan is not None
    assert [s.id for s in plan] == ["auth", "fetch", "render"]


def test_no_applicable_skill_returns_none():
    """Initial state doesn't satisfy any skill's preconditions, and
    the goal is unreachable → None."""
    from verimem.strips import plan_strips

    plan = plan_strips(
        initial_state={"unrelated_state"},
        goal_state={"ui_rendered"},
        skills=_toy_skills(),
    )
    assert plan is None


def test_depth_budget_exhausted_returns_none():
    """A reachable goal but max_depth too small → None."""
    from verimem.strips import plan_strips

    plan = plan_strips(
        initial_state={"have_creds"},
        goal_state={"ui_rendered"},
        skills=_toy_skills(),
        max_depth=2,  # need 3 steps
    )
    assert plan is None


def test_planner_prefers_shortest():
    """Two paths exist: auth→fetch (2 steps) gets data_loaded; or a
    longer detour. BFS guarantees shortest first."""
    from verimem.strips import plan_strips

    # Add a redundant path: pre={have_creds}, post={data_loaded}
    # (bypassing logged_in). Both reach data_loaded; the shortcut
    # is shorter.
    skills = _toy_skills() + [
        Skill(id="shortcut", name="direct_fetch",
              preconditions=["have_creds"],
              postconditions=["data_loaded"]),
    ]
    plan = plan_strips(
        initial_state={"have_creds"},
        goal_state={"data_loaded"},
        skills=skills,
    )
    assert plan is not None
    # Shortest = 1 skill (the shortcut).
    assert len(plan) == 1
    assert plan[0].id == "shortcut"


def test_only_applicable_skills_considered():
    """Skills whose preconditions aren't (yet) satisfied must not
    be applied. The planner must wait until prerequisites are met."""
    from verimem.strips import plan_strips

    plan = plan_strips(
        initial_state={"have_creds"},
        goal_state={"logged_out"},
        skills=_toy_skills(),
    )
    # Must go through auth before logout.
    assert plan is not None
    assert [s.id for s in plan] == ["auth", "logout"]


def test_empty_skill_set_no_plan_unless_goal_already():
    """No skills available + goal not satisfied → None."""
    from verimem.strips import plan_strips

    plan = plan_strips(
        initial_state={"x"},
        goal_state={"y"},
        skills=[],
    )
    assert plan is None
