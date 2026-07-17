"""R44: Memory growth velocity (items per day in rolling window)."""
from __future__ import annotations

import time
from typing import Any


def _items_in_window(items: list[Any], now: float, window_days: float) -> int:
    cutoff = now - window_days * 86400.0
    return sum(
        1 for x in items
        if float(getattr(x, "created_at", 0.0) or 0.0) >= cutoff
    )


def compute_velocity(
    *,
    episodes: list[Any],
    facts: list[Any],
    window_days: float = 7.0,
    now: float | None = None,
) -> dict[str, Any]:
    """Items per day for episodes + facts in a rolling window."""
    if now is None:
        now = time.time()
    n_ep = _items_in_window(episodes, now, window_days)
    n_f = _items_in_window(facts, now, window_days)
    eff_window = max(0.001, window_days)
    return {
        "episodes_per_day": round(n_ep / eff_window, 3),
        "facts_per_day": round(n_f / eff_window, 3),
        "n_episodes_recent": n_ep,
        "n_facts_recent": n_f,
        "window_days": window_days,
    }


__all__ = ["compute_velocity"]
