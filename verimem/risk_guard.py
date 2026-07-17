"""Predictive error-guarding — atomic idea #4 (2026-06-13).

The complement to idea #2 (correction-velocity): #2 fires only when a task
signature has a failure-THEN-success history and hands you the fix. The more
dangerous case has NO fix yet — a task that *keeps* failing. ``predict_outcome``
already estimates p(failure) from similar past episodes (Jaccard on task_text +
outcome — fully grounded, no traces), but it's reachable only on PULL (the
``hippo_outcome_predict`` MCP tool). ``assess_task_risk`` is the thin guard layer
that turns it into a PROACTIVE briefing warning: when the incoming task looks
like one that historically FAILS (high p_failure with enough confidence), flag
it and surface the similar failures so you guard against re-committing the error.

Pure, deterministic, no-LLM. Wiring it into ``briefing.get_briefing`` (next to
the emerging/correction signals, sharing the same single ``memory.all()`` scan)
is the additive step exercised by the wiring tests.
"""
from __future__ import annotations

from typing import Any

from .outcome_predict import predict_outcome


def _empty() -> dict[str, Any]:
    return {
        "is_risky": False,
        "p_failure": 0.0,
        "confidence": 0.0,
        "n_similar": 0,
        "similar_failures": [],
        "reason": "",
    }


def assess_task_risk(
    task_text: str,
    episodes: list[Any],
    *,
    min_failure_prob: float = 0.55,
    min_confidence: float = 0.4,
    top_k_failures: int = 3,
) -> dict[str, Any]:
    """Flag ``task_text`` as risky if similar past episodes mostly FAILED.

    Risky iff ``p_failure >= min_failure_prob`` AND ``confidence >=
    min_confidence`` (i.e. enough similar episodes — predict_outcome's
    confidence is ``min(n_similar/5, 1)``, so the default 0.4 needs >= 2) AND at
    least one similar failure exists to show. Returns ``{is_risky, p_failure,
    confidence, n_similar, similar_failures, reason}``. Side-effect free; safe on
    empty/blank input.
    """
    if not (task_text or "").strip() or not episodes:
        return _empty()

    pred = predict_outcome(task=task_text, episodes=episodes)
    p_failure = float(pred["p_failure"])
    confidence = float(pred["confidence"])
    n_similar = int(pred["n_similar"])
    similar_failures = [
        {"task_text": r.get("task_text", ""), "jaccard": r.get("jaccard", 0.0)}
        for r in pred.get("similar_episodes", [])
        if r.get("outcome") == "failure"
    ][:top_k_failures]

    is_risky = (
        p_failure >= min_failure_prob
        and confidence >= min_confidence
        and bool(similar_failures)
    )
    reason = ""
    if is_risky:
        reason = (
            f"{round(p_failure * 100)}% of {n_similar} similar past tasks FAILED "
            "— review the prior failures before committing the same approach."
        )
    return {
        "is_risky": is_risky,
        "p_failure": p_failure,
        "confidence": confidence,
        "n_similar": n_similar,
        "similar_failures": similar_failures,
        "reason": reason,
    }


__all__ = ["assess_task_risk"]
