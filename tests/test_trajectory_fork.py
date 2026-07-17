"""R1.3: Fork a trajectory from step N (counterfactual replay seed)."""
from __future__ import annotations

import pytest


def _mk():
    from verimem.trajectory import TrajectoryStep
    return [
        TrajectoryStep(step_idx=0, kind="thought", content="reflect"),
        TrajectoryStep(
            step_idx=1, kind="action", content="run nmap",
            tool_name="nmap",
        ),
        TrajectoryStep(step_idx=2, kind="observation", content="ssh open"),
        TrajectoryStep(
            step_idx=3, kind="decision", content="try creds",
            branch_id="A",
        ),
        TrajectoryStep(step_idx=4, kind="action", content="fail creds"),
    ]


def test_fork_preserves_prefix():
    from verimem.trajectory_fork import trajectory_fork
    out = trajectory_fork(_mk(), from_step=3)
    # All steps with step_idx < 3 preserved
    kept = [s for s in out["preserved"] if s.step_idx < 3]
    assert len(kept) == 3


def test_fork_drops_suffix():
    from verimem.trajectory_fork import trajectory_fork
    out = trajectory_fork(_mk(), from_step=3)
    # No preserved step at idx 3 or 4
    assert all(s.step_idx < 3 for s in out["preserved"])


def test_fork_returns_metadata():
    from verimem.trajectory_fork import trajectory_fork
    out = trajectory_fork(_mk(), from_step=2)
    assert "fork_id" in out
    assert "preserved" in out
    assert "branch_point" in out
    assert out["branch_point"] == 2


def test_fork_at_step_0_returns_empty_preserved():
    from verimem.trajectory_fork import trajectory_fork
    out = trajectory_fork(_mk(), from_step=0)
    assert out["preserved"] == []


def test_fork_beyond_max_step_keeps_all():
    from verimem.trajectory_fork import trajectory_fork
    out = trajectory_fork(_mk(), from_step=99)
    assert len(out["preserved"]) == 5  # all kept (nothing to drop)


def test_fork_negative_step_raises():
    from verimem.trajectory_fork import trajectory_fork
    with pytest.raises(ValueError):
        trajectory_fork(_mk(), from_step=-1)


def test_fork_with_counterfactual_seed():
    """If user provides counterfactual_action, append it as step from_step."""
    from verimem.trajectory import TrajectoryStep
    from verimem.trajectory_fork import trajectory_fork

    seed = TrajectoryStep(
        step_idx=3, kind="action", content="try different exploit",
        tool_name="metasploit",
    )
    out = trajectory_fork(_mk(), from_step=3, counterfactual_seed=seed)
    # preserved (0..2) + seed = 4
    assert len(out["preserved"]) == 4
    assert out["preserved"][-1].tool_name == "metasploit"
