"""Skill freshness via exponential decay.

FORGIA pezzo #264 — Wave 63. Score = exp(-(now-last_used)/half_life).
Recent skills score ~1.0, stale skills score ~0.0.
"""
from __future__ import annotations

import math
import time
from typing import Any

from .skill import Skill


def usage_decay(
    skills: list[Skill],
    *,
    now: float | None = None,
    half_life_days: float = 14.0,
    top_k: int = 100,
) -> dict[str, Any]:
    """Compute decay score per skill, sorted descending."""
    t = now if now is not None else time.time()
    half_life_sec = half_life_days * 86400.0
    # exp(-delta / half_life_sec * ln(2))  so that delta=half_life → 0.5.
    decay_const = math.log(2.0) / half_life_sec

    rows: list[dict[str, Any]] = []
    for s in skills:
        lua = float(getattr(s, "last_used_at", 0.0) or 0.0)
        if lua <= 0.0:
            score = 0.0
            days_since: float | None = None
        else:
            delta = max(0.0, t - lua)
            score = math.exp(-delta * decay_const)
            days_since = delta / 86400.0
        rows.append({
            "id": s.id,
            "name": getattr(s, "name", ""),
            "score": float(score),
            "days_since": days_since,
            "last_used_at": lua,
        })

    rows.sort(key=lambda r: -r["score"])
    return {
        "n_total": len(rows),
        "half_life_days": half_life_days,
        "skills": rows[:top_k],
    }


__all__ = ["usage_decay"]
