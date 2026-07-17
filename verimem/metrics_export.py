"""Metrics export in CSV or JSON.

FORGIA pezzo #258 — Wave 57. Dump per-day aggregates for external
dashboards (Grafana/Prometheus/Excel).
"""
from __future__ import annotations

import json
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any


def export_metrics(
    *,
    episodes: list[Any],
    format: str = "csv",
    window_days: int = 30,
) -> str:
    """Aggregate episode metrics per-day, return as CSV or JSON.

    Output rows: `{date, n_success, n_failure, tokens, n_episodes}`.
    """
    if format not in ("csv", "json"):
        raise ValueError(f"format must be 'csv' or 'json'; got {format!r}")

    cutoff = time.time() - window_days * 86400.0
    by_day: dict[str, dict[str, int]] = defaultdict(
        lambda: {"n_success": 0, "n_failure": 0, "tokens": 0,
                  "n_episodes": 0}
    )

    for ep in episodes:
        ts = float(getattr(ep, "created_at", 0.0) or 0.0)
        if ts < cutoff:
            continue
        date_str = datetime.fromtimestamp(
            ts, tz=timezone.utc
        ).strftime("%Y-%m-%d")
        bucket = by_day[date_str]
        outcome = getattr(ep, "outcome", "")
        if outcome == "success":
            bucket["n_success"] += 1
        elif outcome == "failure":
            bucket["n_failure"] += 1
        bucket["tokens"] += int(getattr(ep, "tokens_used", 0) or 0)
        bucket["n_episodes"] += 1

    rows = [
        {"date": d, **counts}
        for d, counts in sorted(by_day.items())
    ]

    if format == "json":
        return json.dumps(rows, indent=2)

    # CSV.
    if not rows:
        return "date,n_success,n_failure,tokens,n_episodes"
    headers = ["date", "n_success", "n_failure", "tokens", "n_episodes"]
    lines = [",".join(headers)]
    for r in rows:
        lines.append(",".join(str(r[h]) for h in headers))
    return "\n".join(lines)


__all__ = ["export_metrics"]
