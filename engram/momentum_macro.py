"""Momentum skill composition — atomic idea #3 (2026-06-13).

The missing DECISION layer between ``recall_chain`` (which computes, per recalled
skill, the forward trajectories taken next with calibrated probabilities) and
``compose_macro`` (which fuses an ordered chain into one executable meta-skill).

``recall_chain`` hands back a flat list of probabilities and leaves the judgement
to the reader — so ``compose_macro`` is a tool nobody triggers, because nothing
flags WHEN a chain has enough momentum to be worth fusing. This module is that
trigger: it picks the recalled skill whose best forward chain is both probable
(``>= min_forward_prob``) and a real multi-skill chain (``>= min_path_len``
distinct steps), and surfaces it as a ready compose recommendation.

Pure, deterministic, no-LLM. Consumes ``recall_chain``'s ``recalls`` list
(``[{skill_id, name, score, forward_plans: [{path, prob, ...}]}]``) and is wired
back into ``recall_chain``'s output as the ``momentum`` field, so it ships to
every caller of the ``hippo_recall_chain`` MCP tool for free.
"""
from __future__ import annotations

from typing import Any


def _collapse(path: list[str]) -> list[str]:
    """Collapse consecutive duplicate skill ids (forward_plan appends sink
    self-loops like B->B; A->B->B is really the A->B chain)."""
    out: list[str] = []
    for s in path:
        if not out or out[-1] != s:
            out.append(s)
    return out


def _empty() -> dict[str, Any]:
    return {
        "has_candidate": False,
        "skill_id": None,
        "skill_name": None,
        "recall_score": 0.0,
        "macro_path": [],
        "forward_prob": 0.0,
        "n_steps": 0,
        "reason": "",
        "n_candidates": 0,
    }


def momentum_macro_candidate(
    recalls: list[dict[str, Any]],
    *,
    min_recall_score: float = 0.0,
    min_forward_prob: float = 0.7,
    min_path_len: int = 2,
) -> dict[str, Any]:
    """Pick the strongest 'momentum' chain among recall_chain's recalls.

    A momentum candidate is a recalled skill (``score >= min_recall_score``)
    whose best forward plan is probable (``prob >= min_forward_prob``) and is a
    real chain of ``>= min_path_len`` *distinct* steps once self-loops collapse.

    Returns ``{has_candidate, skill_id, skill_name, recall_score, macro_path,
    forward_prob, n_steps, reason, n_candidates}``. ``macro_path`` is the ordered
    skill-id chain to feed ``hippo_compose_macro``. Ranks by forward_prob desc,
    then recall_score desc. Side-effect free; safe on empty input.
    """
    candidates: list[dict[str, Any]] = []
    for rec in recalls or []:
        score = float(rec.get("score", 0.0) or 0.0)
        if score < min_recall_score:
            continue
        best: dict[str, Any] | None = None
        for plan in rec.get("forward_plans", []) or []:
            prob = float(plan.get("prob", 0.0) or 0.0)
            if prob < min_forward_prob:
                continue
            chain = _collapse([str(s) for s in plan.get("path", []) or []])
            if len(chain) < min_path_len or len(set(chain)) < 2:
                continue  # single skill / self-loop is not a composable chain
            if best is None or prob > best["forward_prob"]:
                best = {
                    "skill_id": rec.get("skill_id"),
                    "skill_name": rec.get("name"),
                    "recall_score": score,
                    "macro_path": chain,
                    "forward_prob": prob,
                    "n_steps": len(chain) - 1,
                }
        if best is not None:
            candidates.append(best)

    if not candidates:
        return _empty()

    candidates.sort(key=lambda c: (-c["forward_prob"], -c["recall_score"]))
    top = candidates[0]
    path_str = " -> ".join(top["macro_path"])
    top.update({
        "has_candidate": True,
        "reason": (
            f"chain {path_str} followed '{top['skill_name']}' in "
            f"{top['forward_prob']:.0%} of cases — compose into one macro "
            f"(hippo_compose_macro) to skip re-deciding each step."
        ),
        "n_candidates": len(candidates),
    })
    return top


__all__ = ["momentum_macro_candidate"]
