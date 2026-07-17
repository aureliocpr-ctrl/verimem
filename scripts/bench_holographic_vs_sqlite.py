"""Cycle 388 bench — HolographicMemory vs SQLite falsifiable contracts.

A3 honest agenda: separate HRR-pure contribution from cleanup-pool
contribution. SQLite baseline = production semantic.db safe-copy.

Bench protocol:
  1. Sample N=[100, 500, 1000, 2000] synthetic facts
  2. For each N, test 3 configurations:
     A. HRR-pure (cleanup_pool_cap = N/10, severely limits cache)
     B. HRR-cleanup (cleanup_pool_cap = N, full cache)
     C. SQLite emulation (full cache, baseline)
  3. Measure: storage_bytes, write_p99_us, read_p99_us, recall@1

Falsifiable contracts:
  (X1) Configuration A (HRR-pure) recall@1 ≥ 0.5 at N=500
       → if <0.5, B4 HRR-pure thesis falsified at production scale
  (X2) Configuration B storage_size / SQLite storage_size < 0.05 (5%)
       → density gain claim
  (X3) Cliff edge: A.recall@1(N=2000) < A.recall@1(N=100) by ≥ 0.15
       → capacity bound verifiable

A1 ANTI-CONFAB: numbers are predictions. Bench reports actual values.
Negative result accepted per Popperian discipline.

Usage:
    python -m scripts.bench_holographic_vs_sqlite --N 100,500,1000
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import tempfile
import time
from pathlib import Path

import numpy as np


def _gen_facts(n: int, seed: int = 42) -> list[tuple[str, str]]:
    """Generate n synthetic (topic, proposition) tuples deterministically."""
    rng = np.random.default_rng(seed)
    out = []
    for i in range(n):
        # Mix categories for realism
        cat = ["math", "code", "memory", "agent", "graph"][i % 5]
        sub = rng.integers(0, 1000)
        t = f"{cat}/topic_{i:05d}_{sub}"
        # Proposition has token-like richness
        words = [f"w{rng.integers(0, 10_000):05d}" for _ in range(8)]
        p = f"prop_{i:05d}: {' '.join(words)}"
        out.append((t, p))
    return out


def bench_holographic(
    facts: list[tuple[str, str]],
    cleanup_pool_cap: int,
    d: int = 8192,
) -> dict:
    """Bench HolographicMemory at given cleanup_pool_cap."""
    from verimem.holographic_memory import HolographicMemory

    mem = HolographicMemory(d=d, cleanup_pool_cap=cleanup_pool_cap)
    # Write phase
    write_times = []
    for t, p in facts:
        t0 = time.perf_counter()
        mem.remember(t, p)
        write_times.append((time.perf_counter() - t0) * 1e6)
    # Read phase
    correct = 0
    read_times = []
    for t, p_true in facts:
        t0 = time.perf_counter()
        r = mem.recall(t, top_k=1)
        read_times.append((time.perf_counter() - t0) * 1e6)
        if r and r[0]["proposition"] == p_true:
            correct += 1
    s = mem.stats()
    return {
        "n": len(facts),
        "cleanup_pool_cap": cleanup_pool_cap,
        "d": d,
        "storage_bytes": (
            s["aggregate_size_bytes"] + s["bloom_size_bytes"]
        ),
        "write_p99_us": float(np.percentile(write_times, 99)),
        "write_mean_us": float(np.mean(write_times)),
        "read_p99_us": float(np.percentile(read_times, 99)),
        "read_mean_us": float(np.mean(read_times)),
        "recall_at_1": correct / len(facts),
        "correct": correct,
        "aggregate_norm": s["aggregate_norm"],
        "cleanup_pool_size": s["cleanup_pool_size"],
    }


def bench_sqlite(
    facts: list[tuple[str, str]],
) -> dict:
    """Bench SQLite baseline (single-table indexed)."""
    tmpdir = tempfile.mkdtemp(prefix="bench_sqlite_")
    db_path = Path(tmpdir) / "facts.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "CREATE TABLE facts (topic TEXT PRIMARY KEY, proposition TEXT)"
    )
    conn.commit()
    # Write phase
    write_times = []
    for t, p in facts:
        t0 = time.perf_counter()
        conn.execute(
            "INSERT OR REPLACE INTO facts (topic, proposition) VALUES (?, ?)",
            (t, p),
        )
        conn.commit()
        write_times.append((time.perf_counter() - t0) * 1e6)
    # Read phase
    correct = 0
    read_times = []
    for t, p_true in facts:
        t0 = time.perf_counter()
        cur = conn.execute(
            "SELECT proposition FROM facts WHERE topic = ?", (t,),
        )
        row = cur.fetchone()
        read_times.append((time.perf_counter() - t0) * 1e6)
        if row and row[0] == p_true:
            correct += 1
    storage_bytes = db_path.stat().st_size
    conn.close()
    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)
    return {
        "n": len(facts),
        "storage_bytes": storage_bytes,
        "write_p99_us": float(np.percentile(write_times, 99)),
        "write_mean_us": float(np.mean(write_times)),
        "read_p99_us": float(np.percentile(read_times, 99)),
        "read_mean_us": float(np.mean(read_times)),
        "recall_at_1": correct / len(facts),
        "correct": correct,
    }


def run_full_bench(N_list: list[int], d: int = 8192) -> dict:
    """Run bench across N values + configurations A/B/C."""
    results = {"N_list": N_list, "d": d, "runs": []}
    for N in N_list:
        facts = _gen_facts(N)
        print(f"\n[bench] N={N}...", file=sys.stderr)

        # Config A: HRR-pure (cleanup tiny ≈ N/10, forces HRR-only retrieval)
        pure_cap = max(N // 10, 10)
        a = bench_holographic(facts, cleanup_pool_cap=pure_cap, d=d)
        a["config"] = "A_HRR_pure"
        print(
            f"  A pure(cap={pure_cap}): storage={a['storage_bytes']/1024:.1f}KB "
            f"recall@1={a['recall_at_1']:.2%} "
            f"write_p99={a['write_p99_us']:.0f}us "
            f"read_p99={a['read_p99_us']:.0f}us",
            file=sys.stderr,
        )

        # Config B: HRR-cleanup (cleanup full, masks HRR)
        b = bench_holographic(facts, cleanup_pool_cap=N, d=d)
        b["config"] = "B_HRR_cleanup_full"
        print(
            f"  B cleanup_full: storage={b['storage_bytes']/1024:.1f}KB "
            f"recall@1={b['recall_at_1']:.2%} "
            f"write_p99={b['write_p99_us']:.0f}us "
            f"read_p99={b['read_p99_us']:.0f}us",
            file=sys.stderr,
        )

        # Config C: SQLite baseline
        c = bench_sqlite(facts)
        c["config"] = "C_SQLite_baseline"
        print(
            f"  C SQLite: storage={c['storage_bytes']/1024:.1f}KB "
            f"recall@1={c['recall_at_1']:.2%} "
            f"write_p99={c['write_p99_us']:.0f}us "
            f"read_p99={c['read_p99_us']:.0f}us",
            file=sys.stderr,
        )

        # Falsifiable verdict
        density_ratio_b_vs_c = b["storage_bytes"] / max(c["storage_bytes"], 1)
        verdict_pure_recall = (
            "SUPPORTED" if a["recall_at_1"] >= 0.5 else "FALSIFIED"
        )
        verdict_density = (
            "SUPPORTED" if density_ratio_b_vs_c < 0.05 else "FALSIFIED"
        )

        results["runs"].append({
            "N": N,
            "A": a,
            "B": b,
            "C": c,
            "density_B_vs_C_ratio": density_ratio_b_vs_c,
            "X1_pure_recall_verdict": verdict_pure_recall,
            "X2_density_verdict": verdict_density,
        })

    # Cliff edge X3: compare A.recall@1 at N=100 vs N=2000 if both present
    A_recalls = {r["N"]: r["A"]["recall_at_1"] for r in results["runs"]}
    if 100 in A_recalls and 2000 in A_recalls:
        cliff_delta = A_recalls[100] - A_recalls[2000]
        results["X3_cliff_edge_delta"] = cliff_delta
        results["X3_cliff_verdict"] = (
            "SUPPORTED" if cliff_delta >= 0.15 else "FALSIFIED"
        )

    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--N", type=str, default="100,500,1000,2000",
                        help="comma-separated N values")
    parser.add_argument("--d", type=int, default=8192)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    N_list = [int(x) for x in args.N.split(",")]
    t0 = time.time()
    results = run_full_bench(N_list, d=args.d)
    results["elapsed_s"] = time.time() - t0

    text = json.dumps(results, indent=2)
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
