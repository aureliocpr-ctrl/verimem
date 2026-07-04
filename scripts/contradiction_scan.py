"""Cycle #110.B — Standalone contradiction scanner.

Run as a cron / scheduled task / one-off check::

    python -m scripts.contradiction_scan
    python -m scripts.contradiction_scan --similarity 0.8 --tolerance 0.02
    python -m scripts.contradiction_scan --json    # machine-readable output

Reads the live SemanticMemory (resolved via the standard config), runs
``engram.contradiction.scan_corpus``, prints a human summary, and exits
non-zero if any NEW contradictions were detected. Useful as a CI gate
on the corpus or as a periodic job from a process supervisor.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

# Make ``engram`` importable when run as ``python scripts/...``.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engram.config import CONFIG  # noqa: E402
from engram.contradiction import ContradictionStore, scan_corpus  # noqa: E402
from engram.semantic import SemanticMemory  # noqa: E402


def _build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="contradiction_scan",
        description=(
            "Scan the semantic corpus for contradictions and persist the "
            "detected pairs into the contradictions table."
        ),
    )
    p.add_argument(
        "--similarity", type=float, default=0.75,
        help="cosine similarity threshold (default 0.75)",
    )
    p.add_argument(
        "--tolerance", type=float, default=0.05,
        help="numeric value relative tolerance (default 0.05 = 5%)",
    )
    p.add_argument(
        "--no-boolean", action="store_true",
        help="skip boolean clash detection (numeric only)",
    )
    p.add_argument(
        "--json", action="store_true",
        help="print machine-readable JSON summary",
    )
    p.add_argument(
        "--exit-zero", action="store_true",
        help="always exit 0 (default: exit 1 if new clashes detected)",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_argparser().parse_args(argv)

    sm_path = CONFIG.semantic_db
    if not sm_path.exists():
        print(f"semantic DB not found: {sm_path}", file=sys.stderr)
        return 2

    sm = SemanticMemory(db_path=sm_path)
    store = ContradictionStore(sm_path)

    started_at = time.time()
    summary = scan_corpus(
        sm, store=store,
        similarity_threshold=args.similarity,
        value_tolerance=args.tolerance,
        detect_boolean=not args.no_boolean,
    )
    summary["elapsed_s"] = round(time.time() - started_at, 3)
    summary["total_unresolved"] = store.count_unresolved()
    summary["db_path"] = str(sm_path)

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print("=== Contradiction scan ===")
        print(f"DB: {summary['db_path']}")
        print(f"Scanned facts: {summary['scanned_facts']}")
        print(f"New detected: {summary['new_detected']}")
        print(f"Already known: {summary['already_known']}")
        print(f"By kind: {summary['kinds']}")
        print(f"Total unresolved in store: {summary['total_unresolved']}")
        print(f"Elapsed: {summary['elapsed_s']}s")

    if args.exit_zero:
        return 0
    return 1 if summary["new_detected"] > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
