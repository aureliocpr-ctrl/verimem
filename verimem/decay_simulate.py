"""Read-only preview of decay-prune candidates.

FORGIA pezzo #238 — Wave 37. Wraps `Memory.decay_pruning_candidates`
into an inspect-only payload — helps the user decide what to pin
before the next consolidate cycle.
"""
from __future__ import annotations

from typing import Any


def decay_simulate(
    *,
    agent: Any,
    top_k: int = 20,
) -> dict[str, Any]:
    """Return the lowest-salience non-pinned episodes — the ones
    closest to pruning."""
    mem = getattr(agent, "memory", None)
    if mem is None or not hasattr(mem, "decay_pruning_candidates"):
        return {"candidates": [], "n_total": 0, "top_k": top_k}

    try:
        eps = list(mem.decay_pruning_candidates(limit=top_k))
    except Exception:
        eps = []

    candidates = []
    for ep in eps:
        candidates.append({
            "id": getattr(ep, "id", ""),
            "task_text": (getattr(ep, "task_text", "") or "")[:160],
            "outcome": getattr(ep, "outcome", ""),
            "salience_score": float(getattr(ep, "salience_score", 0.0)),
        })
    return {
        "candidates": candidates,
        "n_total": len(candidates),
        "top_k": top_k,
    }


__all__ = ["decay_simulate"]
