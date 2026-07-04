"""R21: Find emerging patterns over time.

Split episodes into recent (last recent_window_days) and historical
(history_window_days but excluding recent). For each task signature,
compute growth_ratio = recent_count / max(historical_count, 1).

Patterns with growth_ratio > min_growth and recent_count >= min_recent
are flagged as "emerging".
"""
from __future__ import annotations

import re
import time
from collections import Counter, defaultdict
from typing import Any

_TOKEN_RE = re.compile(r"[A-Za-z0-9_\-]+")


def _signature(text: str, n: int = 4) -> str:
    toks = [t.lower() for t in _TOKEN_RE.findall(text or "")]
    counter = Counter(toks)
    return ",".join(sorted(t for t, _ in counter.most_common(n)))


def find_emerging_patterns(
    episodes: list[Any],
    *,
    now: float | None = None,
    recent_window_days: float = 7.0,
    history_window_days: float = 60.0,
    min_growth_ratio: float = 2.0,
    min_recent_count: int = 3,
    top_k: int = 30,
) -> dict[str, Any]:
    """Identify task signatures rising in frequency."""
    if now is None:
        now = time.time()
    recent_cutoff = now - recent_window_days * 86400.0
    history_cutoff = now - history_window_days * 86400.0

    recent: dict[str, int] = defaultdict(int)
    historical: dict[str, int] = defaultdict(int)

    for ep in episodes:
        ts = float(getattr(ep, "created_at", 0.0) or 0.0)
        sig = _signature(getattr(ep, "task_text", ""))
        if ts >= recent_cutoff:
            recent[sig] += 1
        elif ts >= history_cutoff:
            historical[sig] += 1

    emerging: list[dict[str, Any]] = []
    for sig, n_recent in recent.items():
        if n_recent < min_recent_count:
            continue
        n_hist = historical.get(sig, 0)
        # Avoid div-by-zero
        denom = max(n_hist, 1)
        growth = n_recent / denom
        if growth >= min_growth_ratio:
            emerging.append({
                "signature": sig,
                "recent_count": n_recent,
                "historical_count": n_hist,
                "growth_ratio": round(growth, 2),
            })

    emerging.sort(key=lambda e: -e["growth_ratio"])
    return {
        "emerging": emerging[:top_k],
        "n_episodes_scanned": len(episodes),
        "recent_window_days": recent_window_days,
        "history_window_days": history_window_days,
    }


__all__ = ["find_emerging_patterns"]
