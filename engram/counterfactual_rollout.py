"""R15: Counterfactual rollout — what-if multi-action simulation.

Given a state and a list of candidate actions, run world_model
simulation on each pair (state, action) against past episodes, then
rank by expected p_success.

Output: rankings + the recommended action (top p_success above
threshold).

Pure-local. Built on R6 world_model.
"""
from __future__ import annotations

from typing import Any

from .world_model import simulate_action


def rollout_actions(
    *,
    state: str,
    actions: list[str],
    past_episodes: list[Any],
    confidence_threshold: float = 0.55,
) -> dict[str, Any]:
    """Run a what-if rollout for each candidate action."""
    rollouts: list[dict[str, Any]] = []
    for action in actions:
        sim = simulate_action(
            state=state, action=action, past_episodes=past_episodes,
        )
        rollouts.append({
            "action": action,
            "p_success": sim["p_success"],
            "p_failure": sim["p_failure"],
            "confidence": sim["confidence"],
            "n_similar": sim["n_similar"],
            "alternative": sim["alternative"],
        })

    # Sort by p_success desc
    rollouts.sort(key=lambda r: -r["p_success"])

    # Recommendation: ONLY the top action when it clears the confidence
    # threshold. Below it there is no grounded pick, so recommended stays None
    # (the full rollouts remain for the caller to inspect). Returning the top
    # regardless made confidence_threshold dead code and dressed an ungrounded
    # guess as an evidence-backed recommendation.
    recommended: str | None = None
    if rollouts and rollouts[0]["p_success"] >= confidence_threshold:
        recommended = rollouts[0]["action"]

    return {
        "rollouts": rollouts,
        "recommended": recommended,
        "n_actions": len(actions),
    }


__all__ = ["rollout_actions"]
