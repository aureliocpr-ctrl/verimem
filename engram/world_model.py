"""R6: World model — predict outcome before acting.

Given a proposed (state, action), simulate what's likely to happen
by aggregating outcomes of similar past episodes weighted by Jaccard
similarity on tokens. If failure is predicted, mine past success
episodes for a candidate alternative action.

This is the predictive/planning layer. Foundation for true planning
(beam search, MCTS) in future rounds.
"""
from __future__ import annotations

import re
from typing import Any

_TOKEN_RE = re.compile(r"[A-Za-z0-9_\-]+")


def _tokens(text: str) -> set[str]:
    return {t.lower() for t in _TOKEN_RE.findall(text or "")}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def _action_phrase(task_text: str, state_tokens: set[str]) -> str:
    """Extract the action part of a past task_text: keep the words whose
    normalized tokens are NOT part of the CURRENT state (order preserved).

    Heuristic, not a parser — but it stops the suggested alternative from
    echoing the other episode's state (its target/stack) as if it were the
    action.
    """
    kept = [
        w for w in (task_text or "").split()
        if (toks := _tokens(w)) and toks.isdisjoint(state_tokens)
    ]
    return " ".join(kept).strip()


def _suggest_alternative(
    state_tokens: set[str],
    action_tokens: set[str],
    past_episodes: list[Any],
) -> tuple[str, str] | None:
    """Find a past success on similar state but DIFFERENT action.

    Returns ``(action_phrase, evidence_id)`` of the best match, or None. The
    action phrase is the episode's task_text minus the current state's tokens,
    so the caller gets the ACTION, not the whole foreign task_text.
    """
    best: tuple[float, str, str] | None = None
    for ep in past_episodes:
        if getattr(ep, "outcome", "") != "success":
            continue
        ep_tokens = _tokens(getattr(ep, "task_text", ""))
        if not ep_tokens:
            continue
        # Penalize if the same action tokens are present
        ep_only_action = ep_tokens - state_tokens
        same_action_ratio = (
            len(ep_only_action & action_tokens) / max(1, len(action_tokens))
        )
        if same_action_ratio > 0.5:
            continue  # essentially same action
        # State similarity
        state_sim = _jaccard(ep_tokens, state_tokens)
        if state_sim < 0.1:
            continue
        score = state_sim
        if best is None or score > best[0]:
            best = (
                score,
                _action_phrase(getattr(ep, "task_text", ""), state_tokens),
                getattr(ep, "id", ""),
            )
    return (best[1], best[2]) if best else None


def simulate_action(
    *,
    state: str,
    action: str,
    past_episodes: list[Any],
    top_k: int = 10,
    similarity_threshold: float = 0.1,
) -> dict[str, Any]:
    """Predict outcome of (state, action) based on past experience.

    Returns:
      - `p_success` / `p_failure`: probabilities (sum ~1)
      - `confidence`: none/low/medium/high based on evidence
      - `n_similar`: count of episodes used
      - `evidence_ids`: ids of similar episodes
      - `alternative`: suggested alternate action (text) if failure
        predicted
      - `rationale`: 1-line reason
    """
    state_tokens = _tokens(state)
    action_tokens = _tokens(action)
    query_tokens = state_tokens | action_tokens

    if not past_episodes or not query_tokens:
        return {
            "p_success": 0.5,
            "p_failure": 0.5,
            "confidence": "none",
            "n_similar": 0,
            "evidence_ids": [],
            "alternative": None,
            "alternative_evidence_id": None,
            "rationale": "no past experience — uniform prior",
        }

    # Score every episode by Jaccard on combined state+action tokens
    scored: list[tuple[float, Any]] = []
    for ep in past_episodes:
        ep_tokens = _tokens(getattr(ep, "task_text", ""))
        sim = _jaccard(query_tokens, ep_tokens)
        if sim >= similarity_threshold:
            scored.append((sim, ep))
    scored.sort(key=lambda t: -t[0])
    top = scored[:top_k]

    if not top:
        alt = _suggest_alternative(state_tokens, action_tokens, past_episodes)
        return {
            "p_success": 0.5,
            "p_failure": 0.5,
            "confidence": "none",
            "n_similar": 0,
            "evidence_ids": [],
            "alternative": alt[0] if alt else None,
            "alternative_evidence_id": alt[1] if alt else None,
            "rationale": "no past episode above similarity threshold",
        }

    # Weighted vote by similarity (Laplace smoothing: 1 each side)
    w_succ = 1.0
    w_fail = 1.0
    for sim, ep in top:
        outcome = getattr(ep, "outcome", "")
        if outcome == "success":
            w_succ += sim
        elif outcome == "failure":
            w_fail += sim
    total = w_succ + w_fail
    p_success = w_succ / total
    p_failure = 1.0 - p_success

    # Confidence: based on count + p polarity
    n = len(top)
    polarity = abs(p_success - 0.5) * 2  # 0..1
    if n >= 3 and polarity >= 0.5:
        confidence = "high"
    elif n >= 2 and polarity >= 0.3:
        confidence = "medium"
    elif n >= 1:
        confidence = "low"
    else:
        confidence = "none"

    alternative: str | None = None
    alternative_evidence_id: str | None = None
    if p_success < 0.5:
        alt = _suggest_alternative(
            state_tokens, action_tokens, past_episodes,
        )
        if alt is not None:
            alternative, alternative_evidence_id = alt

    rationale = (
        f"n={n} similar episodes, p_success={p_success:.2f} "
        f"(polarity={polarity:.2f})"
    )

    return {
        "p_success": round(p_success, 3),
        "p_failure": round(p_failure, 3),
        "confidence": confidence,
        "n_similar": n,
        "evidence_ids": [getattr(ep, "id", "") for _, ep in top],
        "alternative": alternative,
        "alternative_evidence_id": alternative_evidence_id,
        "rationale": rationale,
    }


__all__ = ["simulate_action"]
