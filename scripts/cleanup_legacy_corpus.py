"""Cycle #114 — CLI for the forgettable-bucket cleanup.

Usage::

    # SAFE: dry-run, prints what would happen
    python -m scripts.cleanup_legacy_corpus

    # ACTUALLY delete (default cap=25, opt-in via --apply)
    python -m scripts.cleanup_legacy_corpus --apply --max-forget 25

    # JSON output for piping
    python -m scripts.cleanup_legacy_corpus --json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Make ``engram`` importable when invoked as ``python scripts/...``.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from verimem.config import CONFIG  # noqa: E402
from verimem.legacy_cleanup import cleanup_forgettable  # noqa: E402
from verimem.semantic import SemanticMemory  # noqa: E402


def _build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="cleanup_legacy_corpus",
        description=(
            "Delete the legacy_unverified fact rows the classifier "
            "marks as `forgettable` (short / very-low confidence / "
            "TODO/FIXME/deprecated keyword). Other buckets untouched."
        ),
    )
    p.add_argument(
        "--apply", action="store_true",
        help="actually delete rows. Default is dry-run (no mutation).",
    )
    p.add_argument(
        "--max-forget", type=int, default=None,
        help="cap on the number of rows deleted in this run.",
    )
    p.add_argument(
        "--json", action="store_true",
        help="machine-readable JSON output (no human summary).",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_argparser().parse_args(argv)

    sm_path = CONFIG.semantic_db
    if not sm_path.exists():
        print(f"semantic DB not found: {sm_path}", file=sys.stderr)
        return 2

    sm = SemanticMemory(db_path=sm_path)
    report = cleanup_forgettable(
        sm,
        dry_run=not args.apply,
        max_forget=args.max_forget,
    )
    report["db_path"] = str(sm_path)

    if args.json:
        print(json.dumps(report, indent=2))
        return 0

    mode = "DRY-RUN" if report["dry_run"] else "APPLIED"
    print(f"=== Legacy forgettable cleanup ({mode}) ===")
    print(f"DB: {report['db_path']}")
    print(f"Total legacy_unverified scanned: {report['total_legacy_scanned']}")
    print(f"Eligible for deletion (forgettable bucket): {report['would_forget']}")
    print(f"Actually deleted: {report['forgotten']}")
    if report["samples"]:
        print()
        print("--- Sample candidates ---")
        for s in report["samples"]:
            prop_short = (
                s["proposition"][:120] + "..."
                if len(s["proposition"]) > 120
                else s["proposition"]
            )
            print(
                f"  id={s['fact_id']:<14} conf={s['confidence']:.2f} "
                f"reason={s['bucket_reason']}"
            )
            print(f"    {prop_short}")
    if report["dry_run"] and report["would_forget"] > 0:
        print()
        print("Re-run with --apply to actually delete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
