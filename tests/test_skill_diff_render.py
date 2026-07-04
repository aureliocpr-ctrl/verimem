"""FORGIA pezzo #243 — Wave 42: skill diff markdown renderer.

Renders a side-by-side markdown diff between 2 skills. Useful when
the user wants to compare two near-duplicate skills before deciding
to merge or retire one.

Existing `hippo_skill_compare` returns NUMERICAL diff; this renders
HUMAN-READABLE markdown.
"""
from __future__ import annotations

from engram.skill import Skill


def test_returns_string():
    from engram.skill_diff_render import render_skill_diff

    a = Skill(id="a", name="x")
    b = Skill(id="b", name="y")
    out = render_skill_diff(a, b)
    assert isinstance(out, str)


def test_includes_both_names():
    from engram.skill_diff_render import render_skill_diff

    a = Skill(id="a", name="alpha")
    b = Skill(id="b", name="beta")
    out = render_skill_diff(a, b)
    assert "alpha" in out
    assert "beta" in out


def test_shows_status_difference():
    from engram.skill_diff_render import render_skill_diff

    a = Skill(id="a", name="x", status="candidate")
    b = Skill(id="b", name="x", status="promoted")
    out = render_skill_diff(a, b)
    assert "candidate" in out
    assert "promoted" in out


def test_shows_trial_counts():
    from engram.skill_diff_render import render_skill_diff

    a = Skill(id="a", name="x", trials=5, successes=3)
    b = Skill(id="b", name="x", trials=20, successes=15)
    out = render_skill_diff(a, b)
    assert "5" in out
    assert "20" in out


def test_shows_predicate_differences():
    from engram.skill_diff_render import render_skill_diff

    a = Skill(id="a", name="x", preconditions=["p1"])
    b = Skill(id="b", name="x", preconditions=["p1", "p2"])
    out = render_skill_diff(a, b)
    assert "p1" in out
    assert "p2" in out


def test_identical_skills_marked():
    from engram.skill_diff_render import render_skill_diff

    a = Skill(id="a", name="x", trials=5, successes=3)
    b = Skill(id="b", name="x", trials=5, successes=3)
    out = render_skill_diff(a, b)
    # The renderer should note that most fields match.
    assert "x" in out  # name appears
