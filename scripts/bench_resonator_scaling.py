"""Cycle 392 (2026-05-23) — Resonator scaling experiment D vs M.

A3 honest agenda: cycle 389/390/391 xfail empirico no-hint failure.
Test if INCREASING D / DECREASING M (atoms per role) actually closes
the xfail at N=3 superposition.

Frady 2020 §3.2 informal capacity heuristic:
  - For K=3 roles, capacity scales as D / (M_atom^K * log_factor)
  - Larger D + smaller M → better SNR per fact
  - But: shared codebook is bigger → storage cost

Bench protocol (N=3 facts no-hint, matching_pursuit):
  Configurations:
    A) D=1024, M=64  (cycle 391 baseline)
    B) D=2048, M=64
    C) D=4096, M=32
    D) D=8192, M=16
    E) D=16384, M=8
  For each: 5 seeds, count facts recovered without hint.

Falsifiable (X1): does increasing D close the gap?
  If E (largest D, smallest M) recovers ≥2/3 → SUPPORTED scaling
  If even E fails ≥2/3 → naive resonator truly limited beyond D scaling

Usage: python -m scripts.bench_resonator_scaling
"""
from __future__ import annotations

import argparse
import json
import sys
import time

import numpy as np


def run_n_scaling(d: int, m: int, n_facts_list: list[int],
                  n_seeds: int = 5) -> dict:
    """Cycle 393 — scale N facts at sweet-spot D=4096 M=32 config.

    For each N, generate N distinct random tuples and check matching_pursuit
    recovery rate. Tests where the 3/3 result breaks down.
    """
    from verimem.resonator_memory import ResonatorMemory

    out: list[dict] = []
    for N in n_facts_list:
        rec_per_seed: list[int] = []
        for seed in range(n_seeds):
            mem = ResonatorMemory(
                n_roles=3, atoms_per_role=m, d=d,
                seed=0xA1B2C3D4 + seed * 7,
            )
            rng = np.random.default_rng(seed * 99 + 1)
            facts_in = []
            seen: set[tuple[int, ...]] = set()
            while len(facts_in) < N:
                t = tuple(rng.integers(0, m, size=3).tolist())
                if t in seen:
                    continue
                seen.add(t)
                facts_in.append(t)
            for t in facts_in:
                mem.remember_tuple(t)
            res = mem.recall_all_via_matching_pursuit(
                max_facts=N * 2, n_restarts_per_pass=32,
            )
            correct = sum(1 for f in res["found_facts"] if f in facts_in)
            rec_per_seed.append(correct)
        out.append({
            "n_facts": N,
            "recoveries": rec_per_seed,
            "mean": float(np.mean(rec_per_seed)),
            "max": int(np.max(rec_per_seed)),
            "frac_recovered_mean": float(np.mean(rec_per_seed)) / N,
        })
    return {"d": d, "m": m, "n_seeds": n_seeds, "results": out}


def run_one(d: int, m: int, n_seeds: int = 5,
            facts_in: list[tuple[int, int, int]] | None = None) -> dict:
    """Run one configuration. Returns avg facts recovered."""
    from verimem.resonator_memory import ResonatorMemory

    if facts_in is None:
        facts_in = [(5, 10, 15), (20, 25, 30), (40, 50, 60)]
    # Clamp facts to valid M range
    facts_in = [tuple(min(i, m - 1) for i in t) for t in facts_in]

    recoveries: list[int] = []
    for seed in range(n_seeds):
        mem = ResonatorMemory(
            n_roles=3, atoms_per_role=m, d=d, seed=0xA1B2C3D4 + seed * 7,
        )
        for t in facts_in:
            mem.remember_tuple(t)
        res = mem.recall_all_via_matching_pursuit(
            max_facts=10, n_restarts_per_pass=16,
        )
        correct = sum(1 for f in res["found_facts"] if f in facts_in)
        recoveries.append(correct)
    return {
        "d": d,
        "m": m,
        "facts_in": facts_in,
        "n_seeds": n_seeds,
        "recoveries": recoveries,
        "mean_recovered": float(np.mean(recoveries)),
        "max_recovered": int(np.max(recoveries)),
        "storage_bytes": 3 * m * d * 4 + d * 4,  # codebook + aggregate
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=None)
    parser.add_argument("--mode", default="dvsM",
                        choices=["dvsM", "nscaling"])
    args = parser.parse_args()

    if args.mode == "nscaling":
        print("[bench] N scaling at sweet-spot D=4096 M=32",
              file=sys.stderr)
        out = run_n_scaling(d=4096, m=32,
                            n_facts_list=[3, 5, 10, 20, 40], n_seeds=5)
        text = json.dumps(out, indent=2)
        if args.output:
            from pathlib import Path
            Path(args.output).write_text(text, encoding="utf-8")
        print(text)
        return 0

    configs = [
        ("A", 1024, 64),
        ("B", 2048, 64),
        ("C", 4096, 32),
        ("D", 8192, 16),
        ("E", 16384, 8),
    ]
    results = []
    t0 = time.time()
    for name, d, m in configs:
        print(f"[bench] config {name}: D={d} M={m}...", file=sys.stderr)
        r = run_one(d, m)
        r["config"] = name
        results.append(r)
        print(
            f"  mean recovered={r['mean_recovered']:.2f}/3 "
            f"max={r['max_recovered']}/3 "
            f"storage={r['storage_bytes']/1024:.0f}KB",
            file=sys.stderr,
        )

    # Falsifiable verdict
    best = max(results, key=lambda x: x["mean_recovered"])
    verdict_X1 = (
        "SUPPORTED" if best["mean_recovered"] >= 2.0 else "FALSIFIED"
    )

    payload = {
        "configurations": results,
        "best_config": best["config"],
        "best_mean_recovered": best["mean_recovered"],
        "X1_scaling_verdict": verdict_X1,
        "elapsed_s": time.time() - t0,
    }
    text = json.dumps(payload, indent=2)
    if args.output:
        from pathlib import Path
        Path(args.output).write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
