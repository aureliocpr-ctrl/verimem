"""R27: Render a skill/causal chain as ASCII/markdown.

Useful for dashboards and reports: visualize the auto-planned chain
from skill_composer in human-readable form.
"""
from __future__ import annotations


def test_empty_returns_empty():
    from verimem.chain_visualize import render_chain
    out = render_chain([])
    assert out == ""


def test_single_step():
    from verimem.chain_visualize import render_chain
    plan = [{"skill_id": "s1", "role": "matched", "trigger": "do X"}]
    out = render_chain(plan)
    assert "s1" in out
    assert "do X" in out


def test_multi_step_arrows():
    from verimem.chain_visualize import render_chain
    plan = [
        {"skill_id": "a", "role": "parent", "trigger": "recon"},
        {"skill_id": "b", "role": "parent", "trigger": "fingerprint"},
        {"skill_id": "c", "role": "matched", "trigger": "exploit",
         "match_score": 0.8},
    ]
    out = render_chain(plan)
    assert "a" in out and "b" in out and "c" in out
    # Some arrow indicator
    assert "→" in out or "->" in out or "│" in out


def test_role_markers():
    from verimem.chain_visualize import render_chain
    plan = [
        {"skill_id": "p", "role": "parent", "trigger": "x"},
        {"skill_id": "m", "role": "matched", "trigger": "y",
         "match_score": 0.9},
    ]
    out = render_chain(plan)
    # Matched should look different from parent in some way
    assert "matched" in out.lower() or "▶" in out or "0.9" in out
