"""Cycle #115.A — CLI for the MCP audit-log ROI analyzer.

Usage::

    # Human summary on the live audit log
    python -m scripts.analyze_telemetry

    # JSON output for piping
    python -m scripts.analyze_telemetry --json

    # Custom log file (e.g. archived rotation)
    python -m scripts.analyze_telemetry --log ~/.engram/mcp_audit.log.1

    # Top-N tools by call count
    python -m scripts.analyze_telemetry --top 30

Output answers: which of the 209 hippo_* tools are actually called,
how often, how slow. Used to decide which surface to keep / deprecate.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Make ``engram`` importable when invoked as ``python scripts/...``.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engram.config import CONFIG  # noqa: E402
from engram.telemetry_analyzer import analyze_audit_log  # noqa: E402


def _default_log_path() -> Path:
    """Same logic as `engram/mcp_server.py`._audit_log_path()."""
    import os
    custom = os.environ.get("HIPPO_MCP_AUDIT_LOG", "").strip()
    if custom:
        return Path(custom)
    return CONFIG.data_dir / "mcp_audit.log"


def _build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="analyze_telemetry",
        description=(
            "Aggregate the MCP audit log into a per-tool ROI report: "
            "call counts, latency percentiles, outcome breakdown, "
            "unique caller PIDs."
        ),
    )
    p.add_argument(
        "--log", type=Path, default=None,
        help="path to the audit log (default: <engram_data>/mcp_audit.log).",
    )
    p.add_argument(
        "--json", action="store_true",
        help="machine-readable JSON (no human summary).",
    )
    p.add_argument(
        "--top", type=int, default=20,
        help="show only the top-N tools by call count (default 20).",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_argparser().parse_args(argv)

    log_path = args.log or _default_log_path()
    report = analyze_audit_log(log_path)
    report["log_path"] = str(log_path)

    if args.json:
        print(json.dumps(report, indent=2, default=str))
        return 0

    print(f"=== MCP telemetry report ({report['log_path']}) ===")
    print(f"Total calls: {report['total_calls']}")
    if report["total_calls"] == 0:
        print("(empty audit log)")
        return 0
    print()
    items = sorted(
        report["per_tool"].items(),
        key=lambda kv: kv[1]["count"],
        reverse=True,
    )[: args.top]
    header = (
        f"{'tool':<40} {'count':>7} {'p50_ms':>9} "
        f"{'p99_ms':>9} {'max_ms':>9} {'pids':>5}  outcomes"
    )
    print(header)
    print("-" * len(header))
    for tool, rec in items:
        outcomes_short = ",".join(
            f"{k}={v}" for k, v in rec["outcomes"].items()
        )
        print(
            f"{tool:<40} {rec['count']:>7} "
            f"{rec['latency_p50_ms']:>9.2f} "
            f"{rec['latency_p99_ms']:>9.2f} "
            f"{rec['latency_max_ms']:>9.2f} "
            f"{rec['n_unique_pids']:>5}  {outcomes_short}"
        )
    remaining = max(0, len(report["per_tool"]) - args.top)
    if remaining:
        print(f"... ({remaining} more tools below top-{args.top})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
