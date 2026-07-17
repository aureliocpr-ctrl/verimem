"""R2.1: Causal extraction from success/failure trajectory pair.

The core idea: when two trajectories of *similar* tasks diverge, the
first divergence step is the **causal point**. The action taken in the
success path is the cause of success; the action taken in the failure
path is the cause of failure.

This module formalizes that intuition into a structured signal that
the skill-mining layer (R2.2) consumes.
"""
from __future__ import annotations

from typing import Any

from .trajectory import TrajectoryStep
from .trajectory_diff import trajectory_diff


def _describe_step(step_dict: dict[str, Any] | None) -> str:
    """Human-readable one-line description of a step dict."""
    if not step_dict:
        return "(none)"
    parts: list[str] = []
    kind = step_dict.get("kind", "?")
    parts.append(f"[{kind}]")
    if step_dict.get("tool_name"):
        parts.append(f"tool={step_dict['tool_name']}")
    content = step_dict.get("content", "")
    if content:
        parts.append(content[:80])
    return " ".join(parts)


def _propose_rule(
    success_step: dict[str, Any] | None,
    failure_step: dict[str, Any] | None,
) -> str:
    """Propose a natural-language rule from the divergence."""
    if not success_step and not failure_step:
        return ""
    s_tool = (success_step or {}).get("tool_name")
    f_tool = (failure_step or {}).get("tool_name")
    if s_tool and f_tool and s_tool != f_tool:
        return f"Prefer `{s_tool}` over `{f_tool}` in this context"
    if s_tool and not f_tool:
        return f"Always use `{s_tool}` here (failure path skipped tool call)"
    s_content = (success_step or {}).get("content", "")[:60]
    return f"Do: {s_content}" if s_content else ""


def _confidence(
    div_step: int | None,
    success_step: dict[str, Any] | None,
    failure_step: dict[str, Any] | None,
) -> float:
    """Heuristic confidence: tool-name divergence > content divergence."""
    if div_step is None:
        return 0.0
    if not success_step or not failure_step:
        return 0.4
    s_tool = success_step.get("tool_name")
    f_tool = failure_step.get("tool_name")
    if s_tool and f_tool and s_tool != f_tool:
        return 0.85  # clean tool swap
    if s_tool or f_tool:
        return 0.6  # one side has tool, other not
    return 0.4  # content-only divergence (noisier)


def causal_extract(
    *,
    success_traj: list[TrajectoryStep],
    failure_traj: list[TrajectoryStep],
    success_id: str,
    failure_id: str,
) -> dict[str, Any]:
    """Extract a causal signal from a success/failure trajectory pair."""
    diff = trajectory_diff(success_traj, failure_traj)
    div = diff["first_divergence"]

    if div is None:
        return {
            "divergence_step": None,
            "cause": "",
            "alternative": "",
            "rule": "",
            "confidence": 0.0,
            "evidence": {
                "success_id": success_id,
                "failure_id": failure_id,
                "common_prefix_len": diff["common_prefix_len"],
            },
        }

    # Note: trajectory_diff returns step_a=success, step_b=failure
    # (we passed success first to it).
    success_step = diff["step_a"]
    failure_step = diff["step_b"]

    cause = _describe_step(failure_step)
    alternative = _describe_step(success_step)
    rule = _propose_rule(success_step, failure_step)
    confidence = _confidence(div, success_step, failure_step)

    return {
        "divergence_step": div,
        "cause": cause,
        "alternative": alternative,
        "rule": rule,
        "confidence": confidence,
        "evidence": {
            "success_id": success_id,
            "failure_id": failure_id,
            "common_prefix_len": diff["common_prefix_len"],
            "len_success": diff["len_a"],
            "len_failure": diff["len_b"],
        },
    }


__all__ = ["causal_extract"]
