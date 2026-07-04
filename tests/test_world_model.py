"""R6: World model — predict outcome BEFORE acting.

Given (state, action) and past episodes, simulate what will happen.
Aggregates similar episodes weighted by similarity. If failure looms,
suggest alternative actions from past success in similar states.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class _Ep:
    id: str
    task_text: str
    outcome: str
    final_answer: str = ""


def test_empty_episodes_returns_uncertain():
    from engram.world_model import simulate_action

    out = simulate_action(
        state="target acme.io WordPress",
        action="exploit CVE-2023-6449",
        past_episodes=[],
    )
    assert out["p_success"] == 0.5  # uniform prior
    assert out["confidence"] == "none"
    assert out["n_similar"] == 0


def test_clear_success_pattern():
    from engram.world_model import simulate_action

    eps = [
        _Ep("e1", "target X WordPress + exploit CVE-2023-6449",
            outcome="success"),
        _Ep("e2", "target Y WordPress + exploit CVE-2023-6449",
            outcome="success"),
        _Ep("e3", "target Z WordPress + exploit CVE-2023-6449",
            outcome="success"),
    ]
    out = simulate_action(
        state="target acme.io WordPress",
        action="exploit CVE-2023-6449",
        past_episodes=eps,
    )
    assert out["p_success"] > 0.7
    assert out["confidence"] in {"medium", "high"}
    assert out["n_similar"] >= 2


def test_clear_failure_pattern_with_alternative():
    from engram.world_model import simulate_action

    eps = [
        _Ep("e1", "target X WordPress + aggressive nmap scan",
            outcome="failure", final_answer="WAF banned"),
        _Ep("e2", "target Y WordPress + aggressive nmap scan",
            outcome="failure", final_answer="WAF banned"),
        _Ep("e3", "target X WordPress + passive crtsh enum",
            outcome="success", final_answer="subs found"),
        _Ep("e4", "target Y WordPress + passive crtsh enum",
            outcome="success", final_answer="subs found"),
    ]
    out = simulate_action(
        state="target acme.io WordPress",
        action="aggressive nmap scan",
        past_episodes=eps,
    )
    assert out["p_success"] < 0.5
    # Should suggest an alternative (passive enum)
    assert "alternative" in out
    assert out["alternative"] is not None


def test_no_alternative_when_action_works():
    from engram.world_model import simulate_action

    eps = [
        _Ep("e1", "target X + good action", outcome="success"),
        _Ep("e2", "target Y + good action", outcome="success"),
    ]
    out = simulate_action(
        state="target acme.io",
        action="good action",
        past_episodes=eps,
    )
    # action works → no alternative needed
    # alternative key may be None or absent
    assert out.get("alternative") is None


def test_payload_complete_keys():
    from engram.world_model import simulate_action

    out = simulate_action(
        state="x", action="y", past_episodes=[],
    )
    for k in ("p_success", "p_failure", "confidence",
              "n_similar", "evidence_ids", "alternative", "rationale"):
        assert k in out


def test_evidence_includes_episode_ids():
    from engram.world_model import simulate_action

    eps = [
        _Ep("ep_abc", "X + Y exploit", outcome="success"),
        _Ep("ep_def", "Z + Y exploit", outcome="success"),
    ]
    out = simulate_action(
        state="X", action="Y exploit", past_episodes=eps,
    )
    assert "ep_abc" in out["evidence_ids"] or "ep_def" in out["evidence_ids"]


def test_mixed_outcomes_moderate_confidence():
    from engram.world_model import simulate_action

    eps = [
        _Ep("e1", "X exploit Y", outcome="success"),
        _Ep("e2", "X exploit Y", outcome="failure"),
        _Ep("e3", "X exploit Y", outcome="success"),
        _Ep("e4", "X exploit Y", outcome="failure"),
    ]
    out = simulate_action(
        state="X", action="exploit Y", past_episodes=eps,
    )
    # Mixed: p_success around 0.5
    assert 0.3 <= out["p_success"] <= 0.7


def test_p_success_plus_p_failure_normalized():
    from engram.world_model import simulate_action

    eps = [_Ep("e1", "X y", outcome="success")]
    out = simulate_action(state="X", action="y", past_episodes=eps)
    # Probabilities should sum to ~1
    assert abs(out["p_success"] + out["p_failure"] - 1.0) < 0.01
