"""Audit log summary aggregator.

FORGIA pezzo #259 — Wave 58. Aggregates audit entries: outcome
counts, tool-usage frequency, recent rejections, rate-limit hits.
Useful for forensics dashboards.
"""
from __future__ import annotations

from collections import Counter
from typing import Any


def summarize_audit(
    entries: list[dict[str, Any]],
    *,
    top_k_tools: int = 10,
    top_k_rejections: int = 10,
) -> dict[str, Any]:
    """Aggregate audit entries.

    Each entry should have `tool` and `outcome` keys at minimum.
    Optionally `error` for rejected calls.
    """
    n_total = len(entries)
    outcomes: Counter[str] = Counter()
    tools: Counter[str] = Counter()
    rejections: list[dict[str, Any]] = []

    for entry in entries:
        outcome = entry.get("outcome", "")
        tool = entry.get("tool", "")
        outcomes[outcome] += 1
        tools[tool] += 1
        if outcome.startswith("rejected") or outcome == "error":
            rejections.append({
                "tool": tool,
                "outcome": outcome,
                "error": entry.get("error", ""),
            })

    top_tools = [
        {"tool": t, "count": c}
        for t, c in tools.most_common(top_k_tools)
    ]

    rejections_recent = rejections[-top_k_rejections:][::-1]

    n_rate_limited = outcomes.get("rate_limited", 0)

    parts: list[str] = []
    parts.append(f"{n_total} audit entries.")
    if outcomes:
        ok_count = outcomes.get("ok", 0)
        parts.append(f"{ok_count} ok")
    if n_rate_limited > 0:
        parts.append(f"{n_rate_limited} rate-limited")
    if rejections:
        parts.append(f"{len(rejections)} rejected")
    summary = " · ".join(parts)

    return {
        "n_total": n_total,
        "by_outcome": dict(outcomes),
        "top_tools": top_tools,
        "n_rate_limited": n_rate_limited,
        "recent_rejections": rejections_recent,
        "summary": summary,
    }


__all__ = ["summarize_audit"]
