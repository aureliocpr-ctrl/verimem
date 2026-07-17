"""Structured trajectory for episodes — Round 1 of HippoAgent v2.

Replaces opaque `num_steps:int` with a step-by-step trace including
thoughts, actions (with tool calls), observations and decisions
(branch points). Enables true replay, fork, diff, causal analysis.

Backward compatible: Episode.trajectory is optional. Old episodes
keep working unchanged.

Kinds:
  - "thought": internal reasoning, no tool call
  - "action": tool invocation (records tool_name/args/result)
  - "observation": passive intake of external state
  - "decision": branch point with branch_id (counterfactual seed)
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from typing import Any

_VALID_KINDS = frozenset({"thought", "action", "observation", "decision"})


@dataclass
class TrajectoryStep:
    """One step in an episode trajectory."""

    step_idx: int
    kind: str  # one of _VALID_KINDS
    content: str  # human-readable description
    timestamp: float = field(default_factory=time.time)
    tool_name: str | None = None
    tool_args: dict[str, Any] | None = None
    tool_result: str | None = None
    branch_id: str | None = None  # decision branch identifier

    def __post_init__(self) -> None:
        if self.kind not in _VALID_KINDS:
            raise ValueError(
                f"kind={self.kind!r} not in {sorted(_VALID_KINDS)}"
            )
        if self.step_idx < 0:
            raise ValueError(f"step_idx must be >=0, got {self.step_idx}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> TrajectoryStep:
        return cls(
            step_idx=int(d["step_idx"]),
            kind=str(d["kind"]),
            content=str(d.get("content", "")),
            timestamp=float(d.get("timestamp", 0.0)),
            tool_name=d.get("tool_name"),
            tool_args=d.get("tool_args"),
            tool_result=d.get("tool_result"),
            branch_id=d.get("branch_id"),
        )


def trajectory_to_json(steps: list[TrajectoryStep]) -> str:
    """Serialize a trajectory to JSON string."""
    return json.dumps([s.to_dict() for s in steps], default=str)


def trajectory_from_json(s: str) -> list[TrajectoryStep]:
    """Deserialize a trajectory from JSON string."""
    if not s or s.strip() == "":
        return []
    data = json.loads(s)
    return [TrajectoryStep.from_dict(d) for d in data]


def trajectory_normalize(
    steps: list[TrajectoryStep],
) -> list[TrajectoryStep]:
    """Return steps sorted by step_idx ascending."""
    return sorted(steps, key=lambda s: s.step_idx)


def trajectory_branches(
    steps: list[TrajectoryStep],
) -> dict[str, list[TrajectoryStep]]:
    """Group steps by branch_id. Steps with branch_id=None are skipped."""
    by_branch: dict[str, list[TrajectoryStep]] = {}
    for s in steps:
        if s.branch_id is None:
            continue
        by_branch.setdefault(s.branch_id, []).append(s)
    # Each branch sorted
    for k, v in by_branch.items():
        by_branch[k] = sorted(v, key=lambda s: s.step_idx)
    return by_branch


__all__ = [
    "TrajectoryStep",
    "trajectory_to_json",
    "trajectory_from_json",
    "trajectory_normalize",
    "trajectory_branches",
]
