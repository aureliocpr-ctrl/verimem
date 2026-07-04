"""R1.4: Diff two trajectories, identify discriminating step.

Use case: 2 episodes con stesso task ma outcome diverso (success vs failure).
Il diff trova il primo step in cui divergono = chiave del successo/fallimento.
"""
from __future__ import annotations


def _step(idx, kind, content, **kw):
    from engram.trajectory import TrajectoryStep
    return TrajectoryStep(step_idx=idx, kind=kind, content=content, **kw)


def test_identical_trajectories_no_diff():
    from engram.trajectory_diff import trajectory_diff

    a = [_step(0, "thought", "X"), _step(1, "action", "Y")]
    b = [_step(0, "thought", "X"), _step(1, "action", "Y")]
    out = trajectory_diff(a, b)
    assert out["first_divergence"] is None
    assert out["common_prefix_len"] == 2


def test_diff_at_step_2():
    from engram.trajectory_diff import trajectory_diff

    a = [
        _step(0, "thought", "reflect"),
        _step(1, "action", "scan"),
        _step(2, "action", "exploit_A"),
    ]
    b = [
        _step(0, "thought", "reflect"),
        _step(1, "action", "scan"),
        _step(2, "action", "exploit_B"),
    ]
    out = trajectory_diff(a, b)
    assert out["first_divergence"] == 2
    assert out["common_prefix_len"] == 2


def test_diff_one_shorter():
    from engram.trajectory_diff import trajectory_diff

    a = [_step(0, "thought", "X"), _step(1, "action", "Y")]
    b = [_step(0, "thought", "X")]
    out = trajectory_diff(a, b)
    assert out["first_divergence"] == 1  # b has nothing at idx 1


def test_diff_payload_includes_steps():
    from engram.trajectory_diff import trajectory_diff

    a = [_step(0, "action", "A")]
    b = [_step(0, "action", "B")]
    out = trajectory_diff(a, b)
    assert "step_a" in out
    assert "step_b" in out
    # content differs at index 0
    assert out["step_a"]["content"] == "A"
    assert out["step_b"]["content"] == "B"


def test_diff_compare_by_kind_and_tool():
    """Same content but different tool_name should be a divergence."""
    from engram.trajectory_diff import trajectory_diff

    a = [_step(0, "action", "scan", tool_name="nmap")]
    b = [_step(0, "action", "scan", tool_name="masscan")]
    out = trajectory_diff(a, b)
    assert out["first_divergence"] == 0


def test_diff_empty_pair():
    from engram.trajectory_diff import trajectory_diff
    out = trajectory_diff([], [])
    assert out["first_divergence"] is None
    assert out["common_prefix_len"] == 0


def test_diff_one_empty():
    from engram.trajectory_diff import trajectory_diff
    out = trajectory_diff([_step(0, "thought", "X")], [])
    assert out["first_divergence"] == 0


def test_diff_summary_string():
    from engram.trajectory_diff import trajectory_diff

    a = [_step(0, "thought", "X"), _step(1, "action", "A")]
    b = [_step(0, "thought", "X"), _step(1, "action", "B")]
    out = trajectory_diff(a, b)
    assert "summary" in out
    assert "step 1" in out["summary"].lower() or "step=1" in out["summary"].lower()
