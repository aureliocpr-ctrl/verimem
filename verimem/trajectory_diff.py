"""R1.4: Diff two trajectories — find the discriminating step.

Use case: pair a successful and a failed episode of the same task family;
the first divergence is the causal point. This is the foundation of
HippoAgent's causal reasoning layer (Round 2).
"""
from __future__ import annotations

from typing import Any

from .trajectory import TrajectoryStep, trajectory_normalize


def _step_signature(s: TrajectoryStep) -> tuple:
    """Compare-key: ignores timestamps but considers kind/tool/args/content."""
    return (
        s.kind,
        s.tool_name,
        repr(s.tool_args) if s.tool_args else None,
        s.content,
    )


def trajectory_diff(
    a: list[TrajectoryStep],
    b: list[TrajectoryStep],
) -> dict[str, Any]:
    """Compare two trajectories step-by-step.

    Returns: `{first_divergence, common_prefix_len, step_a, step_b, summary}`.
    `first_divergence` is None if the trajectories match for as long as they go
    (one may be longer; if so we still report the first index where the
    other has nothing).
    """
    na = trajectory_normalize(a)
    nb = trajectory_normalize(b)
    min_len = min(len(na), len(nb))

    first_divergence: int | None = None
    common_prefix_len = 0
    for i in range(min_len):
        sa = _step_signature(na[i])
        sb = _step_signature(nb[i])
        if sa != sb:
            first_divergence = i
            break
        common_prefix_len += 1

    # One trajectory shorter than the other — that index is a divergence
    if first_divergence is None and len(na) != len(nb):
        first_divergence = min_len

    step_a: dict[str, Any] | None = None
    step_b: dict[str, Any] | None = None
    if first_divergence is not None:
        if first_divergence < len(na):
            step_a = na[first_divergence].to_dict()
        if first_divergence < len(nb):
            step_b = nb[first_divergence].to_dict()

    summary = _summary(first_divergence, common_prefix_len, len(na), len(nb))

    return {
        "first_divergence": first_divergence,
        "common_prefix_len": common_prefix_len,
        "step_a": step_a,
        "step_b": step_b,
        "summary": summary,
        "len_a": len(na),
        "len_b": len(nb),
    }


def _summary(div: int | None, prefix: int, la: int, lb: int) -> str:
    if div is None:
        return f"identical (length {la})"
    return (
        f"diverged at step {div} after {prefix} common steps "
        f"(len_a={la}, len_b={lb})"
    )


__all__ = ["trajectory_diff"]
