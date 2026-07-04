"""R15: Counterfactual rollout — simulate N candidate actions from a state.

Given a state and a list of candidate actions, simulate each one
against past episodes (via world_model) and rank by expected reward.

Output: ranked list of actions with predicted outcomes, plus the
top recommendation.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class _Ep:
    id: str
    task_text: str
    outcome: str


def test_empty_actions_returns_no_rollout():
    from engram.counterfactual_rollout import rollout_actions
    out = rollout_actions(state="x", actions=[], past_episodes=[])
    assert out["rollouts"] == []


def test_single_action_predicted():
    from engram.counterfactual_rollout import rollout_actions

    eps = [_Ep("e1", "x exploit Y", "success") for _ in range(3)]
    out = rollout_actions(
        state="x", actions=["exploit Y"], past_episodes=eps,
    )
    assert len(out["rollouts"]) == 1
    r = out["rollouts"][0]
    assert "p_success" in r


def test_ranking_picks_best_action():
    from engram.counterfactual_rollout import rollout_actions

    eps = [
        _Ep("s1", "x passive crtsh", "success"),
        _Ep("s2", "x passive crtsh", "success"),
        _Ep("s3", "x passive crtsh", "success"),
        _Ep("f1", "x aggressive nmap", "failure"),
        _Ep("f2", "x aggressive nmap", "failure"),
        _Ep("f3", "x aggressive nmap", "failure"),
    ]
    out = rollout_actions(
        state="target x",
        actions=["aggressive nmap", "passive crtsh"],
        past_episodes=eps,
    )
    assert out["recommended"] == "passive crtsh"


def test_payload_keys():
    from engram.counterfactual_rollout import rollout_actions
    out = rollout_actions(state="x", actions=["a"], past_episodes=[])
    for k in ("rollouts", "recommended", "n_actions"):
        assert k in out


def test_each_rollout_has_required_keys():
    from engram.counterfactual_rollout import rollout_actions
    out = rollout_actions(state="x", actions=["a", "b"], past_episodes=[])
    for r in out["rollouts"]:
        for k in ("action", "p_success", "p_failure", "confidence"):
            assert k in r


def test_recommended_is_highest_p_success():
    from engram.counterfactual_rollout import rollout_actions

    eps = [
        _Ep(f"s{i}", "win action X", "success") for i in range(5)
    ] + [
        _Ep(f"f{i}", "lose action Y", "failure") for i in range(5)
    ]
    out = rollout_actions(
        state="state",
        actions=["action X", "action Y"],
        past_episodes=eps,
    )
    assert out["recommended"] == "action X"


def test_none_recommended_when_all_uncertain():
    from engram.counterfactual_rollout import rollout_actions
    out = rollout_actions(
        state="novel state",
        actions=["unknown action"],
        past_episodes=[],
    )
    # No past evidence → recommended may be None or just the only candidate
    assert out["recommended"] in (None, "unknown action")
