"""FORGIA pezzo #52 — clean transient bench data dirs.

The harness writes per-bench data trees under
`/tmp/hippo_*` (Linux) / `%TEMP%\\hippo_*` (Windows). They accumulate
quickly during a series of runs and waste disk. This script lists +
optionally removes them.

Usage:
    python scripts/clean_bench_data.py            # dry-run (default)
    python scripts/clean_bench_data.py --apply    # actually remove

Will NOT touch the production `<project>/data/` tree — only the
sibling `hippo_*` named bench dirs in tempfile.gettempdir().
"""
from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from pathlib import Path


def main() -> int:
    import time
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--apply", action="store_true",
                   help="actually delete (default is dry-run).")
    p.add_argument("--prefix", default="hippo_",
                   help="match dir names starting with this prefix.")
    p.add_argument("--older-than-hours", type=float, default=0.0,
                   help="only consider dirs whose mtime is older than "
                        "this many hours (FORGIA #98; 0 = no filter).")
    p.add_argument("--keep-latest", type=int, default=0,
                   help="keep the N most recent dirs (by mtime), delete "
                        "the rest (FORGIA #107; 0 = no preservation).")
    args = p.parse_args()

    tmp = Path(tempfile.gettempdir())
    candidates = sorted(d for d in tmp.iterdir()
                        if d.is_dir() and d.name.startswith(args.prefix))
    if args.older_than_hours > 0:
        cutoff = time.time() - args.older_than_hours * 3600
        candidates = [d for d in candidates if d.stat().st_mtime < cutoff]
    if args.keep_latest > 0:
        # FORGIA #107: keep the N most recent (by mtime), drop the rest.
        candidates_sorted = sorted(candidates, key=lambda d: d.stat().st_mtime,
                                    reverse=True)
        candidates = candidates_sorted[args.keep_latest:]

    total_bytes = 0
    for d in candidates:
        size = sum(f.stat().st_size for f in d.rglob("*") if f.is_file())
        total_bytes += size
        action = "DELETE" if args.apply else "would delete"
        print(f"  [{action}] {d}  ({size / 1024 / 1024:.1f} MB)")
        if args.apply:
            try:
                shutil.rmtree(d)
            except Exception as exc:  # noqa: BLE001
                print(f"    ERROR: {exc}", file=sys.stderr)

    print(f"\nTotal: {len(candidates)} dirs, {total_bytes / 1024 / 1024:.1f} MB")
    if not args.apply:
        print("(dry-run; pass --apply to actually delete)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
