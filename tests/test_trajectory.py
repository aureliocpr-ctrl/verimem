"""ROUND 1.1: Trajectory schema + serialize/deserialize.

Pezzo fondazionale per causal reasoning, fork, replay.
Backward compatible: episodi senza trajectory continuano a funzionare.
"""
from __future__ import annotations

import json

import pytest


def test_step_kinds():
    from verimem.trajectory import TrajectoryStep

    s = TrajectoryStep(step_idx=0, kind="thought", content="I should check files")
    assert s.kind == "thought"
    assert s.tool_name is None


def test_step_with_tool():
    from verimem.trajectory import TrajectoryStep

    s = TrajectoryStep(
        step_idx=1, kind="action", content="list files",
        tool_name="ls", tool_args={"path": "/tmp"},
        tool_result="file1.txt\nfile2.txt",
    )
    assert s.tool_name == "ls"
    assert s.tool_args == {"path": "/tmp"}


def test_step_validation_kind():
    from verimem.trajectory import TrajectoryStep

    # Invalid kind raises
    with pytest.raises(ValueError):
        TrajectoryStep(step_idx=0, kind="invalid_kind", content="x")


def test_step_validation_step_idx_negative():
    from verimem.trajectory import TrajectoryStep

    with pytest.raises(ValueError):
        TrajectoryStep(step_idx=-1, kind="thought", content="x")


def test_to_dict_roundtrip():
    from verimem.trajectory import TrajectoryStep, trajectory_from_json, trajectory_to_json

    steps = [
        TrajectoryStep(step_idx=0, kind="thought", content="reflect"),
        TrajectoryStep(
            step_idx=1, kind="action", content="run nmap",
            tool_name="nmap", tool_args={"target": "10.0.0.1"},
            tool_result="port 22 open",
        ),
        TrajectoryStep(
            step_idx=2, kind="observation", content="ssh available"
        ),
        TrajectoryStep(
            step_idx=3, kind="decision",
            content="try default creds first",
            branch_id="branch_a",
        ),
    ]
    j = trajectory_to_json(steps)
    parsed = json.loads(j)
    assert isinstance(parsed, list)
    assert len(parsed) == 4
    restored = trajectory_from_json(j)
    assert len(restored) == 4
    assert restored[1].tool_name == "nmap"
    assert restored[3].branch_id == "branch_a"


def test_empty_trajectory_serialization():
    from verimem.trajectory import trajectory_from_json, trajectory_to_json

    assert trajectory_to_json([]) == "[]"
    assert trajectory_from_json("[]") == []


def test_from_json_robust_to_missing_optional():
    from verimem.trajectory import trajectory_from_json

    # minimal step (no tool_name, no branch_id)
    j = '[{"step_idx": 0, "kind": "thought", "content": "ok"}]'
    out = trajectory_from_json(j)
    assert out[0].tool_name is None
    assert out[0].branch_id is None


def test_step_sorting():
    """Steps stored out-of-order should sort by step_idx."""
    from verimem.trajectory import (
        TrajectoryStep,
        trajectory_normalize,
    )

    steps = [
        TrajectoryStep(step_idx=2, kind="thought", content="c"),
        TrajectoryStep(step_idx=0, kind="thought", content="a"),
        TrajectoryStep(step_idx=1, kind="thought", content="b"),
    ]
    sorted_steps = trajectory_normalize(steps)
    assert [s.content for s in sorted_steps] == ["a", "b", "c"]


def test_branch_ids_grouping():
    """Steps with same branch_id form a path."""
    from verimem.trajectory import (
        TrajectoryStep,
        trajectory_branches,
    )

    steps = [
        TrajectoryStep(step_idx=0, kind="thought", content="root"),
        TrajectoryStep(
            step_idx=1, kind="action", content="try A", branch_id="A"
        ),
        TrajectoryStep(
            step_idx=2, kind="observation", content="A failed",
            branch_id="A",
        ),
        TrajectoryStep(
            step_idx=3, kind="action", content="try B", branch_id="B"
        ),
        TrajectoryStep(
            step_idx=4, kind="observation", content="B success",
            branch_id="B",
        ),
    ]
    branches = trajectory_branches(steps)
    assert "A" in branches and "B" in branches
    assert len(branches["A"]) == 2
    assert len(branches["B"]) == 2


def test_step_dict_returns_clean_dict():
    from verimem.trajectory import TrajectoryStep

    s = TrajectoryStep(step_idx=5, kind="action", content="x")
    d = s.to_dict()
    assert d["step_idx"] == 5
    assert d["kind"] == "action"
    assert d["content"] == "x"
    assert "timestamp" in d
