"""Cycle #54 — proactive-briefing telemetry reader.

Reads the JSONL log written by the UserPromptSubmit hook
(`~/.engram/audit/briefing.jsonl`) and produces:
  - global stats (n firings, hit rate, latency P50/P95)
  - top_matched histogram (helps tune `min_matched`)
  - suggested_min_matched: best threshold that maximises
    (#firings_with_hits) while keeping #zero_hits below a budget

This is observability only — no model retraining, no auto-apply.
The suggested values are advisory; the user (Aurelio) decides
whether to update env ENGRAM_BRIEFING_MIN_MATCHED.

Schema of each line in briefing.jsonl (cycle #54):
    ts: float (Unix)
    prompt_excerpt: str (≤80 chars)
    n_keywords: int
    n_hits: int
    n_dup_filtered: int
    top_matched: int      # how many kw matched in best hit
    top_id: str (fact id)
    min_matched_used: int # the threshold THIS firing used
    latency_ms: float
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    k = (len(s) - 1) * p / 100.0
    f = int(k)
    c = min(f + 1, len(s) - 1)
    if f == c:
        return s[f]
    return s[f] + (s[c] - s[f]) * (k - f)


def compute_stats(
    jsonl_path: Path, *, max_records: int = 1000,
) -> dict[str, Any]:
    """Read the last `max_records` entries (tail) and aggregate.

    Returns a dict with: n_firings, hit_rate, n_zero_hits,
    n_dup_filtered_total, avg_keywords, avg_latency_ms,
    p50_latency_ms, p95_latency_ms, top_matched_histogram (dict),
    suggested_min_matched (int — heuristic), suggested_rationale.
    """
    if not jsonl_path.exists():
        return {
            "ok": True,
            "n_firings": 0,
            "hit_rate": 0.0,
            "n_zero_hits": 0,
            "n_dup_filtered_total": 0,
            "avg_keywords": 0.0,
            "avg_latency_ms": 0.0,
            "p50_latency_ms": 0.0,
            "p95_latency_ms": 0.0,
            "top_matched_histogram": {},
            "suggested_min_matched": 2,
            "suggested_rationale": "no data yet — default 2",
        }

    records: list[dict[str, Any]] = []
    try:
        with jsonl_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except Exception:
                    continue
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"read failed: {exc}"}

    # Tail to last max_records
    records = records[-max_records:]
    n = len(records)
    if n == 0:
        return compute_stats(Path("/nonexistent/path"))

    n_with_hits = sum(1 for r in records if int(r.get("n_hits", 0)) > 0)
    n_zero_hits = n - n_with_hits
    n_dup_total = sum(int(r.get("n_dup_filtered", 0)) for r in records)
    avg_kw = (
        sum(int(r.get("n_keywords", 0)) for r in records) / n if n else 0.0
    )
    latencies = [float(r.get("latency_ms", 0.0)) for r in records]
    avg_lat = sum(latencies) / n if n else 0.0
    p50 = _percentile(latencies, 50.0)
    p95 = _percentile(latencies, 95.0)

    hist_counter = Counter()
    for r in records:
        m = int(r.get("top_matched", 0))
        if m > 0:
            hist_counter[m] += 1
    hist = dict(sorted(hist_counter.items()))

    # Suggested min_matched heuristic:
    # - If hit_rate < 30% and zero_hits dominate → suggest LOWER min_matched
    #   (current is too strict, missing real matches)
    # - If many firings have very high top_matched (≥5) → can raise
    #   min_matched without losing useful hits
    # - Otherwise: keep current.
    current = int(records[-1].get("min_matched_used", 2))
    suggested = current
    rationale = "current threshold appears balanced"
    hit_rate = n_with_hits / n if n else 0.0
    if hit_rate < 0.30 and current > 1:
        suggested = current - 1
        rationale = (
            f"hit_rate={hit_rate:.0%} is low; try min_matched={suggested} "
            f"to surface more candidates"
        )
    elif hit_rate > 0.80 and current < 4:
        # Many firings hit; check if we can be more selective
        high_quality_count = sum(
            1 for r in records
            if int(r.get("top_matched", 0)) >= current + 1
        )
        if high_quality_count >= n * 0.5:
            suggested = current + 1
            rationale = (
                f"hit_rate={hit_rate:.0%} high AND {high_quality_count} "
                f"firings have top_matched>={current + 1}; can tighten to "
                f"min_matched={suggested}"
            )

    return {
        "ok": True,
        "n_firings": n,
        "hit_rate": round(hit_rate, 3),
        "n_zero_hits": n_zero_hits,
        "n_dup_filtered_total": n_dup_total,
        "avg_keywords": round(avg_kw, 2),
        "avg_latency_ms": round(avg_lat, 2),
        "p50_latency_ms": round(p50, 2),
        "p95_latency_ms": round(p95, 2),
        "top_matched_histogram": hist,
        "suggested_min_matched": suggested,
        "suggested_rationale": rationale,
    }


__all__ = ["compute_stats"]
