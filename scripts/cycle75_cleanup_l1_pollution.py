"""Cycle #75 - Cleanup script for L1-SYNTAX pollution.

Reads facts from the live semantic DB, detects XML-polluted
propositions, sanitizes them in place via `store()` (INSERT OR
REPLACE on id, idempotent).

Usage:
  python scripts/cycle75_cleanup_l1_pollution.py            # dry-run
  python scripts/cycle75_cleanup_l1_pollution.py --apply    # write

Backup of semantic.db must exist before --apply (we already created
~/.engram/semantic/semantic.db.cycle75-backup-<ts> in cycle prep).
"""
from __future__ import annotations

import argparse
import os
import sys
from dataclasses import replace
from pathlib import Path

from verimem.semantic import Fact, SemanticMemory  # noqa: F401  (kept for callers)
from verimem.syntax_pollution import sanitize_proposition, scan_facts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="Actually write changes.")
    ap.add_argument("--db", default=None, help="Override DB path (default ~/.engram/semantic/semantic.db).")
    ap.add_argument("--limit", type=int, default=10000, help="Max facts to scan.")
    args = ap.parse_args()

    db_path = Path(args.db) if args.db else Path(os.path.expanduser("~/.engram/semantic/semantic.db"))
    if not db_path.exists():
        print(f"ERROR: DB not found at {db_path}", file=sys.stderr)
        return 1

    print(f"DB: {db_path}")
    print(f"Mode: {'APPLY' if args.apply else 'DRY-RUN'}")
    print()

    mem = SemanticMemory(db_path=db_path)
    facts = mem.list_facts(limit=args.limit, offset=0)
    print(f"Loaded {len(facts)} facts")

    report = scan_facts(facts)
    print(f"Polluted detected: {report['n_polluted']}/{report['n_total']} ({100*report['n_polluted']/max(1,report['n_total']):.1f}%)")
    print()

    if report["n_polluted"] == 0:
        print("Nothing to clean.")
        return 0

    # Build a lookup id->Fact so we can replay with the original metadata
    by_id = {f.id: f for f in facts}

    fixed = 0
    skipped = 0
    sample_lines: list[str] = []
    for p in report["polluted"]:
        orig = by_id.get(p["id"])
        if orig is None:
            skipped += 1
            continue
        new_prop = sanitize_proposition(orig.proposition)
        if not new_prop.strip():
            # Sanitize stripped everything — refuse to overwrite with empty.
            skipped += 1
            sample_lines.append(f"  SKIP empty after sanitize: id={p['id']}")
            continue
        if new_prop == orig.proposition:
            # No actual change (defensive)
            skipped += 1
            continue
        # rescan2 fix 2026-06-02: replace() preserva TUTTA la provenance
        # (status / verified_by / superseded_by / writer_role /
        # trigger_keywords / source_signature / lineage_to / ...). Ricostruire
        # Fact() campo-per-campo azzerava quei campi al re-store (un 'verified'
        # tornava 'model_claim', un 'superseded' tornava live): una "pulizia"
        # che corrompeva la memoria.
        new_fact = replace(orig, proposition=new_prop)
        if args.apply:
            mem.store(new_fact)
        fixed += 1
        if len(sample_lines) < 5:
            sample_lines.append(
                f"  FIX id={orig.id[:12]} "
                f"before_len={len(orig.proposition)} after_len={len(new_prop)} "
                f"markers={p['markers']}"
            )

    print(f"Would fix: {fixed}")
    print(f"Skipped:   {skipped} (empty-after-sanitize or no-op)")
    print()
    print("Sample actions:")
    for line in sample_lines:
        print(line)

    if not args.apply:
        print()
        print("Dry-run complete. Re-run with --apply to commit changes.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
