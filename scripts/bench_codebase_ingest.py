"""Cycle #143 (2026-05-18 sera) — real benchmark for codebase_ingest.

Bench the AST pattern extractor against the HippoAgent repo itself.
The temp SemanticMemory is destroyed at exit — production ``~/.engram``
is never touched.

Measures:
    [1] per-file extraction p50/p95/p99 (pure AST, no DB)
    [2] full ingest_codebase duration + pattern counts
    [3] idempotency overhead: second run wall clock vs first
"""
from __future__ import annotations

import argparse
import statistics
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engram.codebase_ingest import (
    extract_patterns_from_file,
    ingest_codebase,
)
from engram.semantic import SemanticMemory


def _percentile(xs: list[float], p: float) -> float:
    if not xs:
        return 0.0
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(len(xs) * p))]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repo", type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="path to repo to ingest (default: hippoagent itself)",
    )
    parser.add_argument("--max-files", type=int, default=2000)
    args = parser.parse_args()
    repo: Path = args.repo

    # [1] per-file extraction latency on engram/ + tests/ subset.
    py_files = list((repo / "engram").rglob("*.py")) + \
               list((repo / "tests").rglob("*.py"))
    py_files = [p for p in py_files if "__pycache__" not in p.parts][:120]
    per_file: list[float] = []
    pattern_count = 0
    for p in py_files:
        t0 = time.perf_counter()
        ps = extract_patterns_from_file(p, repo_name=repo.name,
                                        file_ref=f"file:{p.relative_to(repo).as_posix()}")
        per_file.append((time.perf_counter() - t0) * 1000.0)
        pattern_count += len(ps)
    print(f"[1] extract_patterns_from_file × {len(per_file)} files: "
          f"mean={statistics.mean(per_file):.2f}ms "
          f"p50={_percentile(per_file, .5):.2f}ms "
          f"p95={_percentile(per_file, .95):.2f}ms "
          f"p99={_percentile(per_file, .99):.2f}ms "
          f"max={max(per_file):.2f}ms — extracted {pattern_count} patterns")

    # [2] full ingest with persistence (fresh tmp SM).
    with tempfile.TemporaryDirectory() as td:
        sm = SemanticMemory(db_path=Path(td) / "ing.db")
        t0 = time.perf_counter()
        s1 = ingest_codebase(repo, sm=sm, max_files=args.max_files)
        d1 = (time.perf_counter() - t0)
        print(f"[2] ingest_codebase 1st run on {repo.name}: "
              f"{d1*1000:.0f}ms — files={s1['files_parsed']} "
              f"extracted={s1['patterns_extracted']} "
              f"persisted={s1['patterns_persisted']} "
              f"errors={s1['errors_skipped']}")

        # [3] idempotency overhead — second run on same SM.
        t0 = time.perf_counter()
        s2 = ingest_codebase(repo, sm=sm, max_files=args.max_files)
        d2 = (time.perf_counter() - t0)
        print(f"[3] ingest_codebase 2nd run (idempotency): "
              f"{d2*1000:.0f}ms — extracted={s2['patterns_extracted']} "
              f"persisted={s2['patterns_persisted']} (must be 0)")
        assert s2["patterns_persisted"] == 0, (
            "idempotency violated: 2nd run persisted new facts"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
