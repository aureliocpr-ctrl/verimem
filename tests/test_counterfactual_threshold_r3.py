"""Audit 3-round #22 (anti-confab): rollout_actions must actually gate the
recommendation on confidence_threshold.

The `if p_success >= threshold ... elif rollouts: recommended = top` branch set
`recommended` to the top action in BOTH arms, so the threshold gated nothing — a
0.2-p_success action was still returned as `recommended`, i.e. an ungrounded
guess presented as evidence-backed (the docstring promises "top p_success above
threshold"). Fix: below threshold -> recommended is None; the full rollouts stay
available for the caller to inspect.
"""
from __future__ import annotations

import verimem.counterfactual_rollout as cr


def _mock_sim(scores: dict[str, float]):
    def sim(**kw):
        p = scores[kw["action"]]
        return {
            "p_success": p, "p_failure": 1.0 - p, "confidence": 0.6,
            "n_similar": 3, "alternative": None,
        }
    return sim


def test_recommended_none_when_top_below_threshold(monkeypatch) -> None:
    monkeypatch.setattr(cr, "simulate_action", _mock_sim({"a": 0.3, "b": 0.2}))
    out = cr.rollout_actions(
        state="s", actions=["a", "b"], past_episodes=[],
        confidence_threshold=0.55,
    )
    assert out["recommended"] is None, \
        "nessuna azione sopra soglia -> nessuna raccomandazione fondata"
    assert len(out["rollouts"]) == 2, "i rollout restano per l'ispezione"


def test_recommended_picks_above_threshold(monkeypatch) -> None:
    """Guard: an action above threshold is still recommended (top by p_success)."""
    monkeypatch.setattr(cr, "simulate_action", _mock_sim({"bad": 0.2, "good": 0.8}))
    out = cr.rollout_actions(
        state="s", actions=["bad", "good"], past_episodes=[],
        confidence_threshold=0.55,
    )
    assert out["recommended"] == "good", "la top sopra soglia resta raccomandata"
