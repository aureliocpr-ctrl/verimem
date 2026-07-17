"""R1.2: Render trajectory as markdown."""
from __future__ import annotations


def _mk():
    from verimem.trajectory import TrajectoryStep
    return [
        TrajectoryStep(step_idx=0, kind="thought", content="reason"),
        TrajectoryStep(
            step_idx=1, kind="action", content="run nmap",
            tool_name="nmap", tool_args={"target": "10.0.0.1"},
            tool_result="port 22 open\nport 80 open",
        ),
        TrajectoryStep(step_idx=2, kind="observation", content="2 ports up"),
        TrajectoryStep(
            step_idx=3, kind="decision", content="try ssh first",
            branch_id="ssh-path",
        ),
    ]


def test_empty_returns_empty_string():
    from verimem.trajectory_render import trajectory_to_markdown
    assert trajectory_to_markdown([]).strip() == ""


def test_render_contains_kind_markers():
    from verimem.trajectory_render import trajectory_to_markdown
    md = trajectory_to_markdown(_mk())
    assert "thought" in md.lower()
    assert "action" in md.lower()
    assert "observation" in md.lower()
    assert "decision" in md.lower()


def test_render_includes_tool_calls():
    from verimem.trajectory_render import trajectory_to_markdown
    md = trajectory_to_markdown(_mk())
    assert "nmap" in md
    assert "10.0.0.1" in md


def test_render_branch_id_visible():
    from verimem.trajectory_render import trajectory_to_markdown
    md = trajectory_to_markdown(_mk())
    assert "ssh-path" in md


def test_render_truncate_long_tool_result():
    from verimem.trajectory import TrajectoryStep
    from verimem.trajectory_render import trajectory_to_markdown

    long_result = "x" * 5000
    steps = [TrajectoryStep(
        step_idx=0, kind="action", content="big call",
        tool_name="t", tool_result=long_result,
    )]
    md = trajectory_to_markdown(steps, max_tool_result_chars=500)
    # Must include truncation marker
    assert "..." in md or "truncated" in md.lower()
    assert len(md) < 3000  # not exploded


def test_render_sorts_by_step_idx():
    from verimem.trajectory import TrajectoryStep
    from verimem.trajectory_render import trajectory_to_markdown

    # purposely out of order
    steps = [
        TrajectoryStep(step_idx=2, kind="thought", content="C"),
        TrajectoryStep(step_idx=0, kind="thought", content="A"),
        TrajectoryStep(step_idx=1, kind="thought", content="B"),
    ]
    md = trajectory_to_markdown(steps)
    pos_a = md.find("A")
    pos_b = md.find("B")
    pos_c = md.find("C")
    assert pos_a < pos_b < pos_c
