"""Cycle 367 (2026-05-23) — ENGRAM DASHBOARD WIDGET.

Diagnostic visibility over the engram syscall bridge stack:
  - audit log tail (recent ops)
  - per-op circuit state snapshot (op_supervisor)
  - rate-limit recent calls per op
  - token verification stats (parses last N audit entries)

CLI entry: `python -m engram.dashboard_widget --tail 20 --json` or
plain text default. Designed to be wrapped by clp dashboard subcommand
or invoked stand-alone for ops monitoring.

A3 honest: NOT singolarità. Diagnostic widget. Engineering value:
single-glance summary of the cycle 362-368 stack health, no manual
grep through audit JSONL or supervisor introspection.

API:
  collect_state() -> dict:
    {
      "audit_tail_recent": [...],
      "audit_summary_by_op": {op: count_per_status},
      "circuit_states": {op: snapshot},
      "rate_limit_recent": {op: recent_calls_in_window},
      "manifest_ops": [...],
      "timestamp": float,
    }

  render_text(state) -> str (human-readable)
  render_json(state) -> str (machine-readable)
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from typing import Any


def collect_state(tail_n: int = 50) -> dict[str, Any]:
    """Snapshot the full engram supervision tree state.

    Returns single dict aggregating audit + circuit + rate-limit +
    manifest. All sources read-only, no side effects.
    """
    from engram.op_supervisor import get_default_supervisor
    from engram.syscall_bridge import (
        _RATE_BUCKETS,
        ENGRAM_OPS_MANIFEST,
        engram_audit_tail,
    )

    tail = engram_audit_tail(n=tail_n)

    # Summary by (op, ok/blocked_by)
    summary: dict[str, Counter] = {}
    for rec in tail:
        op = rec.get("op", "?")
        bucket = summary.setdefault(op, Counter())
        if rec.get("ok"):
            bucket["ok"] += 1
        else:
            bucket[rec.get("blocked_by", "unknown_block")] += 1

    # Circuit states from supervisor
    sup = get_default_supervisor()
    circuits = sup.snapshot_all()

    # Rate-limit recent counts (current window snapshot)
    rate_now: dict[str, int] = {}
    now = time.time()
    for op, bucket in _RATE_BUCKETS.items():
        recent = [t for t in bucket if t >= now - 1.0]
        rate_now[op] = len(recent)

    return {
        "timestamp": now,
        "audit_tail_recent": tail,
        "audit_summary_by_op": {op: dict(c) for op, c in summary.items()},
        "circuit_states": circuits,
        "rate_limit_recent": rate_now,
        "manifest_ops": sorted(ENGRAM_OPS_MANIFEST.keys()),
        "stack_layers": [
            "L1 mesh_memory (cross-instance recall, cycle 362)",
            "L2 resonant_merge (Hopfield interpolation, cycle 363)",
            "L3 syscall_bridge (typed boundary + audit, cycle 364)",
            "L4 op_supervisor (circuit breaker, cycle 365)",
            "L5 capability_token (HMAC authz, cycle 368)",
        ],
    }


def render_text(state: dict) -> str:
    """Human-readable rendering."""
    lines: list[str] = []
    lines.append("╔" + "═" * 68 + "╗")
    lines.append("║  ENGRAM DASHBOARD — supervision tree snapshot              ║")
    lines.append("║  " + time.strftime(
        "%Y-%m-%d %H:%M:%S", time.localtime(state["timestamp"])
    ) + " " * 38 + "║")
    lines.append("╚" + "═" * 68 + "╝")

    lines.append("")
    lines.append("Stack layers:")
    for layer in state["stack_layers"]:
        lines.append(f"  • {layer}")

    lines.append("")
    lines.append(f"Manifest ops ({len(state['manifest_ops'])}): "
                 + ", ".join(state["manifest_ops"]))

    lines.append("")
    lines.append("Circuit states:")
    if not state["circuit_states"]:
        lines.append("  (no ops tracked yet — supervisor cold)")
    else:
        for op, snap in state["circuit_states"].items():
            mark = {
                "closed": "✓",
                "open": "✗",
                "half_open": "◐",
            }.get(snap["circuit"], "?")
            lines.append(
                f"  {mark} {op:<22s} circuit={snap['circuit']:<10s} "
                f"failures={snap['n_total_failures']:<3d} "
                f"successes={snap['n_total_successes']:<3d}"
            )

    lines.append("")
    lines.append("Rate-limit current window (calls/last 1s):")
    if not state["rate_limit_recent"]:
        lines.append("  (no recent calls)")
    else:
        for op, n in sorted(state["rate_limit_recent"].items()):
            bar = "█" * min(n, 20)
            lines.append(f"  {op:<22s} {n:>3d} {bar}")

    lines.append("")
    lines.append(f"Audit summary (last {len(state['audit_tail_recent'])} entries):")
    if not state["audit_summary_by_op"]:
        lines.append("  (audit log empty)")
    else:
        for op, c in state["audit_summary_by_op"].items():
            total = sum(c.values())
            ok = c.get("ok", 0)
            line = f"  {op:<22s} total={total:<3d} ok={ok:<3d}"
            blocked = {k: v for k, v in c.items() if k != "ok"}
            if blocked:
                blocked_str = ", ".join(f"{k}={v}" for k, v in blocked.items())
                line += f"  blocked: {blocked_str}"
            lines.append(line)

    return "\n".join(lines)


def render_json(state: dict) -> str:
    """Machine-readable rendering."""
    return json.dumps(state, indent=2, default=str)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tail", type=int, default=50,
                        help="Audit tail entries to summarize (default 50)")
    parser.add_argument("--json", action="store_true",
                        help="Emit JSON instead of text")
    args = parser.parse_args()

    state = collect_state(tail_n=args.tail)
    print(render_json(state) if args.json else render_text(state))
    return 0


if __name__ == "__main__":
    sys.exit(main())
