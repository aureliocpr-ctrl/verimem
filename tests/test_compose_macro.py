"""FORGIA pezzo #235 — Wave 34: skill composition into meta-skill.

Takes N ordered skills and synthesises a single SCHEMA-stage skill
that encapsulates the chain. Useful when the user observes a stable
recurrent sequence and wants to consolidate it into a single
callable unit.

The composed skill:
  - name = derived from constituent names ("schema:auth->fetch->render")
  - trigger = concatenated triggers
  - body = "Apply A, then B, then C"
  - parent_skills = [A.id, B.id, C.id]
  - preconditions = first skill's preconditions (what enters the chain)
  - postconditions = last skill's postconditions (what exits)
  - stage = "schema"
  - status = "candidate" (must earn promotion through trials)
"""
from __future__ import annotations

from verimem.skill import Skill


def test_empty_returns_none():
    from verimem.compose_macro import compose_macro

    out = compose_macro([])
    assert out is None


def test_single_skill_returns_copy():
    from verimem.compose_macro import compose_macro

    s = Skill(id="x", name="alpha", trigger="t")
    out = compose_macro([s])
    # Single-skill composition is degenerate: return None (nothing
    # to compose).
    assert out is None


def test_two_skill_chain():
    from verimem.compose_macro import compose_macro

    a = Skill(id="a", name="auth", trigger="login",
              preconditions=["have_creds"],
              postconditions=["logged_in"])
    b = Skill(id="b", name="fetch", trigger="fetch data",
              preconditions=["logged_in"],
              postconditions=["data_loaded"])
    out = compose_macro([a, b])
    assert out is not None
    assert out.stage == "schema"
    assert out.status == "candidate"
    # Predicates: enter = first pre, exit = last post.
    assert out.preconditions == ["have_creds"]
    assert out.postconditions == ["data_loaded"]
    # Lineage.
    assert "a" in out.parent_skills
    assert "b" in out.parent_skills


def test_name_auto_derived():
    from verimem.compose_macro import compose_macro

    skills = [
        Skill(id="a", name="auth"),
        Skill(id="b", name="fetch"),
        Skill(id="c", name="render"),
    ]
    out = compose_macro(skills)
    assert out is not None
    assert "auth" in out.name
    assert "fetch" in out.name
    assert "render" in out.name


def test_custom_name_overrides_auto():
    from verimem.compose_macro import compose_macro

    skills = [Skill(id="a", name="x"), Skill(id="b", name="y")]
    out = compose_macro(skills, name="my_custom_macro")
    assert out is not None
    assert out.name == "my_custom_macro"


def test_body_describes_sequence():
    from verimem.compose_macro import compose_macro

    skills = [
        Skill(id="a", name="auth"),
        Skill(id="b", name="fetch"),
    ]
    out = compose_macro(skills)
    assert out is not None
    assert "auth" in out.body
    assert "fetch" in out.body


def test_inherits_first_pre_last_post_even_when_middle_irrelevant():
    """The chain's entry/exit is determined by the endpoints, not
    the middle steps."""
    from verimem.compose_macro import compose_macro

    skills = [
        Skill(id="a", name="a", preconditions=["P_in"]),
        Skill(id="b", name="b"),
        Skill(id="c", name="c", postconditions=["P_out"]),
    ]
    out = compose_macro(skills)
    assert out is not None
    assert out.preconditions == ["P_in"]
    assert out.postconditions == ["P_out"]
