"""Outcome timeseries: per-day or per-week success/failure counts.

FORGIA pezzo #224 — Wave 23. Powers the "trends over time" view —
are we improving? Pure local aggregation.
"""
from __future__ import annotations

import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

_BUCKET_SECS = {
    "day": 86400,
    "week": 86400 * 7,
}


def _bucket_floor(ts: float, bucket: str) -> float:
    """Snap a timestamp down to the bucket boundary.

    Week buckets are Monday-aligned (ISO 8601). Since the Unix
    epoch (1970-01-01) is a Thursday, raw modulo gives Thursday-
    aligned weeks — we shift by 4 days to land on Monday.
    """
    if bucket == "week":
        day = int(ts // 86400)
        days_since_monday = (day - 4) % 7
        return float((day - days_since_monday) * 86400)
    secs = _BUCKET_SECS.get(bucket, 86400)
    return float(int(ts // secs) * secs)


def outcome_timeseries(
    episodes: list[Any],
    *,
    bucket: str = "day",
    window_days: int = 30,
) -> dict[str, Any]:
    """Aggregate episode outcomes into time buckets.

    Args:
      - `episodes`: iterable of episode-likes with `outcome` and
        `created_at`.
      - `bucket`: `"day"` (86400s) or `"week"` (7d). Other values
        fall back to `"day"`.
      - `window_days`: only episodes newer than `now - window_days`
        contribute. Default 30 days.

    Returns: `{buckets, bucket_kind, window_days}` where each bucket
    is `{bucket_start, date, n_success, n_failure}`. Sorted by
    `bucket_start` ASC.
    """
    cutoff = time.time() - window_days * 86400.0
    by_bucket: dict[float, dict[str, int]] = defaultdict(
        lambda: {"n_success": 0, "n_failure": 0}
    )

    for ep in episodes:
        ts = float(getattr(ep, "created_at", 0.0))
        if ts < cutoff:
            continue
        outcome = getattr(ep, "outcome", "")
        floor = _bucket_floor(ts, bucket)
        if outcome == "success":
            by_bucket[floor]["n_success"] += 1
        elif outcome == "failure":
            by_bucket[floor]["n_failure"] += 1

    buckets: list[dict[str, Any]] = []
    for start, counts in sorted(by_bucket.items()):
        date_str = datetime.fromtimestamp(
            start, tz=timezone.utc
        ).strftime("%Y-%m-%d")
        buckets.append({
            "bucket_start": start,
            "date": date_str,
            "n_success": counts["n_success"],
            "n_failure": counts["n_failure"],
        })

    return {
        "buckets": buckets,
        "bucket_kind": bucket if bucket in _BUCKET_SECS else "day",
        "window_days": window_days,
    }


__all__ = ["outcome_timeseries"]
