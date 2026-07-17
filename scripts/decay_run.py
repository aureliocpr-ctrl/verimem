"""Cycle #110.C — Standalone confidence decay runner.

Usage::

    python -m scripts.decay_run
    python -m scripts.decay_run --tau-days 14 --floor 0.1
    python -m scripts.decay_run --dry-run --json

Reads the live SemanticMemory (via CONFIG.semantic_db), applies the
exponential decay formula to every fact's confidence, and either
persists or previews the updates.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Make ``engram`` importable when invoked as ``python scripts/...``.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from verimem.config import CONFIG  # noqa: E402
from verimem.decay_job import SEC_PER_DAY, run_decay_pass  # noqa: E402
from verimem.semantic import SemanticMemory  # noqa: E402


def _build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="decay_run",
        description=(
            "Apply exponential confidence decay to every fact in the "
            "semantic corpus."
        ),
    )
    p.add_argument(
        "--tau-days", type=float, default=30.0,
        help="decay time-constant in days (default 30; half-life ~21d)",
    )
    p.add_argument(
        "--floor", type=float, default=0.05,
        help="minimum confidence (default 0.05)",
    )
    p.add_argument(
        "--dry-run", action="store_true",
        help="preview the pass without persisting changes",
    )
    p.add_argument(
        "--json", action="store_true",
        help="print machine-readable JSON summary",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_argparser().parse_args(argv)

    sm_path = CONFIG.semantic_db
    if not sm_path.exists():
        print(f"semantic DB not found: {sm_path}", file=sys.stderr)
        return 2

    sm = SemanticMemory(db_path=sm_path)
    summary = run_decay_pass(
        sm,
        tau_seconds=args.tau_days * SEC_PER_DAY,
        floor=args.floor,
        dry_run=args.dry_run,
    )
    summary["tau_days"] = args.tau_days
    summary["db_path"] = str(sm_path)

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print("=== Confidence decay pass ===")
        print(f"DB: {summary['db_path']}")
        print(f"tau: {summary['tau_days']} days "
              f"(half-life ~{round(summary['tau_days'] * 0.693, 1)}d)")
        print(f"floor: {summary['floor']}")
        print(f"Facts seen: {summary['facts_seen']}")
        print(f"Facts updated: {summary['facts_updated']}")
        print(f"Avg confidence before: {summary['avg_confidence_before']}")
        print(f"Avg confidence after : {summary['avg_confidence_after']}")
        print(f"Mode: {'DRY-RUN (no writes)' if summary['dry_run'] else 'WRITE'}")
        print(f"Elapsed: {summary['elapsed_s']}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
