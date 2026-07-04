"""Cycle #110.D — Standalone legacy-corpus audit CLI.

Usage::

    python -m scripts.audit_legacy_corpus
    python -m scripts.audit_legacy_corpus --status-filter any
    python -m scripts.audit_legacy_corpus --sample-per-bucket 10 --json

Reads the live SemanticMemory (via CONFIG.semantic_db) and classifies
fact in one of three buckets (verified_on_rereading | forgettable |
recoverable). REPORT ONLY -- no mutation.

When invoked WITHOUT --json, prints a human-readable summary + a few
sample propositions per bucket so Aurelio can decide promote / forget
/ supersede manually.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Make ``engram`` importable when invoked as ``python scripts/...``.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engram.config import CONFIG  # noqa: E402
from engram.legacy_audit import audit_legacy_corpus  # noqa: E402
from engram.semantic import SemanticMemory  # noqa: E402


def _build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="audit_legacy_corpus",
        description=(
            "Classify the legacy_unverified fact population into 3 "
            "buckets for human triage."
        ),
    )
    p.add_argument(
        "--status-filter", default="legacy_unverified",
        choices=("legacy_unverified", "any"),
        help=(
            "Which population to audit. ``legacy_unverified`` "
            "requires the cycle 109 schema (PR #44+). On pre-#44 "
            "corpora, use ``any``."
        ),
    )
    p.add_argument(
        "--sample-per-bucket", type=int, default=5,
        help="how many sample fact to include per bucket in the report",
    )
    p.add_argument(
        "--json", action="store_true",
        help="machine-readable JSON output (suitable for piping)",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_argparser().parse_args(argv)

    sm_path = CONFIG.semantic_db
    if not sm_path.exists():
        print(f"semantic DB not found: {sm_path}", file=sys.stderr)
        return 2

    sm = SemanticMemory(db_path=sm_path)
    summary = audit_legacy_corpus(
        sm,
        status_filter=args.status_filter,
        sample_per_bucket=args.sample_per_bucket,
    )
    summary["db_path"] = str(sm_path)

    if args.json:
        print(json.dumps(summary, indent=2))
        return 0

    print("=== Legacy corpus audit ===")
    print(f"DB: {summary['db_path']}")
    print(f"Status filter: {summary['status_filter']}")
    print(f"Total classified: {summary['total_classified']}")
    print()
    print("Bucket counts:")
    for bucket, count in summary["bucket_counts"].items():
        print(f"  {bucket:<25} {count}")
    print()
    for bucket, items in summary["samples"].items():
        if not items:
            continue
        print(f"--- Samples ({bucket}) ---")
        for it in items:
            prop_short = (it["proposition"][:100] + "...") \
                if len(it["proposition"]) > 100 else it["proposition"]
            print(
                f"  id={it['fact_id']:<14} conf={it['confidence']:.2f} "
                f"age={it['age_days']:6.1f}d reason={it['bucket_reason']}"
            )
            print(f"    {prop_short}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
