"""Cycle #115.A — Analyze the MCP audit log into a per-tool ROI report.

The MCP server (cycle #115.A onwards) emits one JSONL record per call,
including `latency_ms`. This module aggregates the log into a tabular
report used by:

* the CLI `scripts/analyze_telemetry.py` (human + JSON output),
* Aurelio's ROI assessment of HippoAgent: which of the 209 MCP tools
  are actually called, how often, how slow.

The function is pure (no side effects) and tolerant of malformed lines
(skipped, not raised) so it can run safely on a partially-corrupted log.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any


def _percentile(values: list[float], pct: float) -> float:
    """Linear-interpolation percentile (matches numpy.percentile default).
    `pct` in [0, 100]. Returns 0.0 on empty input."""
    if not values:
        return 0.0
    s = sorted(values)
    if len(s) == 1:
        return s[0]
    k = (len(s) - 1) * (pct / 100.0)
    lo = int(k)
    hi = min(lo + 1, len(s) - 1)
    frac = k - lo
    return s[lo] + (s[hi] - s[lo]) * frac


def analyze_audit_log(path: Path | str) -> dict[str, Any]:
    """Parse the JSONL audit log and return a per-tool aggregate.

    Returns::

        {
            "total_calls": int,
            "per_tool": {
                "<tool_name>": {
                    "count": int,
                    "latency_p50_ms": float,
                    "latency_p99_ms": float,
                    "latency_max_ms": float,
                    "n_unique_pids": int,
                    "outcomes": { "<outcome>": int, ... },
                },
                ...
            },
        }
    """
    p = Path(path)
    if not p.exists() or p.stat().st_size == 0:
        return {"total_calls": 0, "per_tool": {}}

    per_tool_latencies: dict[str, list[float]] = defaultdict(list)
    per_tool_count: dict[str, int] = defaultdict(int)
    per_tool_pids: dict[str, set[int]] = defaultdict(set)
    per_tool_outcomes: dict[str, dict[str, int]] = defaultdict(
        lambda: defaultdict(int),
    )

    total = 0
    with open(p, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            tool = rec.get("tool")
            if not tool:
                continue
            total += 1
            per_tool_count[tool] += 1
            outcome = rec.get("outcome", "unknown")
            per_tool_outcomes[tool][outcome] += 1
            pid = rec.get("caller_pid")
            if pid is not None:
                per_tool_pids[tool].add(int(pid))
            lat = rec.get("latency_ms")
            if isinstance(lat, (int, float)):
                per_tool_latencies[tool].append(float(lat))

    per_tool: dict[str, Any] = {}
    for tool, count in per_tool_count.items():
        lats = per_tool_latencies[tool]
        per_tool[tool] = {
            "count": count,
            "latency_p50_ms": _percentile(lats, 50.0) if lats else 0.0,
            "latency_p99_ms": _percentile(lats, 99.0) if lats else 0.0,
            "latency_max_ms": max(lats) if lats else 0.0,
            "n_unique_pids": len(per_tool_pids[tool]),
            "outcomes": dict(per_tool_outcomes[tool]),
        }

    return {"total_calls": total, "per_tool": per_tool}
