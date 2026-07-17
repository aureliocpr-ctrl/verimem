"""FORGIA pezzo #242 — Wave 41: STRIPS chain markdown renderer.

Renders a plan (output of `hippo_plan_strips` or
`hippo_chain_validate`) as readable markdown for display in the
chat UI. Pure-string utility.
"""
from __future__ import annotations

from verimem.skill import Skill


def test_empty_chain_renders_minimal():
    from verimem.chain_render import render_chain_markdown

    out = render_chain_markdown(initial_state=[], chain=[])
    assert "# Plan" in out or "## Plan" in out
    # Empty chain is a valid no-op plan.


def test_renders_step_table():
    from verimem.chain_render import render_chain_markdown

    chain = [
        Skill(id="a", name="auth",
              preconditions=["have_creds"],
              postconditions=["logged_in"]),
    ]
    out = render_chain_markdown(
        initial_state=["have_creds"], chain=chain,
    )
    assert "auth" in out
    assert "have_creds" in out
    assert "logged_in" in out
    # Markdown table syntax.
    assert "|" in out


def test_includes_step_indices():
    from verimem.chain_render import render_chain_markdown

    chain = [
        Skill(id=f"s{i}", name=f"skill{i}",
              postconditions=[f"p{i}"])
        for i in range(3)
    ]
    out = render_chain_markdown(initial_state=[], chain=chain)
    assert "1" in out and "2" in out and "3" in out


def test_renders_initial_and_final_state():
    from verimem.chain_render import render_chain_markdown

    chain = [
        Skill(id="a", name="a",
              preconditions=["x"], postconditions=["y"]),
    ]
    out = render_chain_markdown(initial_state=["x"], chain=chain)
    # Both initial (x) and final (y) state predicates appear.
    assert "x" in out
    assert "y" in out


def test_goal_check_when_provided():
    from verimem.chain_render import render_chain_markdown

    chain = [
        Skill(id="a", name="a",
              preconditions=["x"], postconditions=["y"]),
    ]
    out = render_chain_markdown(
        initial_state=["x"], chain=chain, goal_state=["y"],
    )
    # Should mention goal satisfaction.
    assert "goal" in out.lower() or "satisfied" in out.lower()


def test_returns_string():
    from verimem.chain_render import render_chain_markdown

    out = render_chain_markdown(initial_state=[], chain=[])
    assert isinstance(out, str)
