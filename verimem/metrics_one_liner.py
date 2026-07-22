"""Compact one-line metrics summary.

FORGIA pezzo #247 — Wave 46. Single string for status-bar / CI /
SessionStart context. Format:
  `verimem: E ep (S✓/F✗), N facts, K skills (P prom), T tok 7d`
"""
from __future__ import annotations

import time
from typing import Any


def metrics_one_liner(
    *,
    agent: Any,
    window_days: int = 7,
) -> str:
    """Return a single-line status summary."""
    cutoff = time.time() - window_days * 86400.0

    # Episodes.
    ep_count = 0
    n_success = 0
    n_failure = 0
    tokens_window = 0
    try:
        for ep in agent.memory.all():
            ep_count += 1
            outcome = getattr(ep, "outcome", "")
            if outcome == "success":
                n_success += 1
            elif outcome == "failure":
                n_failure += 1
            ts = float(getattr(ep, "created_at", 0.0) or 0.0)
            if ts >= cutoff:
                tokens_window += int(
                    getattr(ep, "tokens_used", 0) or 0
                )
    except Exception:
        pass

    # Facts.
    n_facts = 0
    try:
        n_facts = int(agent.semantic.count())
    except Exception:
        pass

    # Skills.
    n_skills = 0
    n_promoted = 0
    try:
        for s in agent.skills.all():
            n_skills += 1
            if getattr(s, "status", "") == "promoted":
                n_promoted += 1
    except Exception:
        pass

    return (
        f"verimem: {ep_count} ep ({n_success}✓/{n_failure}✗), "
        f"{n_facts} facts, {n_skills} skills ({n_promoted} prom), "
        f"{tokens_window} tok {window_days}d"
    )


__all__ = ["metrics_one_liner"]
