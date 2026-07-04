"""R1.3: Fork a trajectory from step N — seed for counterfactual replay.

A fork preserves all steps with step_idx < from_step. The caller then
appends new steps to explore an alternative path. Optionally a
`counterfactual_seed` step is appended automatically at position
`from_step`, so the agent can run with a fully-formed starting state.

Returns: dict with fork_id (unique), branch_point (from_step),
and preserved (list of TrajectoryStep).
"""
from __future__ import annotations

import secrets
from typing import Any

from .trajectory import TrajectoryStep, trajectory_normalize


def trajectory_fork(
    steps: list[TrajectoryStep],
    *,
    from_step: int,
    counterfactual_seed: TrajectoryStep | None = None,
) -> dict[str, Any]:
    """Fork a trajectory at step `from_step` to allow counterfactual play.

    Args:
      - `steps`: original trajectory.
      - `from_step`: split point (steps with idx < from_step are kept).
      - `counterfactual_seed`: optional new step to append at `from_step`.

    Returns: `{fork_id, branch_point, preserved}`.
    """
    if from_step < 0:
        raise ValueError(f"from_step must be >=0, got {from_step}")

    norm = trajectory_normalize(steps)
    preserved = [s for s in norm if s.step_idx < from_step]

    if counterfactual_seed is not None:
        # Force seed's step_idx to from_step for consistency.
        seed = TrajectoryStep(
            step_idx=from_step,
            kind=counterfactual_seed.kind,
            content=counterfactual_seed.content,
            timestamp=counterfactual_seed.timestamp,
            tool_name=counterfactual_seed.tool_name,
            tool_args=counterfactual_seed.tool_args,
            tool_result=counterfactual_seed.tool_result,
            branch_id=counterfactual_seed.branch_id or f"fork_{secrets.token_hex(3)}",
        )
        preserved.append(seed)

    fork_id = f"fork_{secrets.token_hex(4)}"
    return {
        "fork_id": fork_id,
        "branch_point": from_step,
        "preserved": preserved,
    }


__all__ = ["trajectory_fork"]
