"""Cycle 280 (2026-05-23) — Replicated injection bench (N_inject × N_seed).

Addresses cycle 256 §5.7 caveat "single injection per k". Run N_inject
different injection seeds × N_seed partition seeds. Total N_inject ×
N_seed paired pre/post comparisons per k value.

Foundation for §5.7 statistical rigorization: plateau k=25-50 may be
sampling artifact or real; this script tests it.

Usage:
    python -m scripts.bench_replicated_injection \\
        --auto-copy --k 50 --N-inject 5 --N-seed 5 \\
        --output replicated_k50.json
"""
from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
import tempfile
import time
from pathlib import Path

import networkx as nx
import numpy as np


def _partition_jaccard(p1: list[set[str]], p2: list[set[str]]) -> float:
    """Re-implementation of partition Jaccard (copy from bench_observer_shift
    for self-containedness)."""
    def co_pairs(part: list[set[str]]) -> set[frozenset[str]]:
        out: set[frozenset[str]] = set()
        for c in part:
            members = sorted(c)
            for i in range(len(members)):
                for j in range(i + 1, len(members)):
                    out.add(frozenset({members[i], members[j]}))
        return out
    pairs_1 = co_pairs(p1)
    pairs_2 = co_pairs(p2)
    union = pairs_1 | pairs_2
    if not union:
        return 0.0
    return 1.0 - (len(pairs_1 & pairs_2) / len(union))


def _louvain_partition(db_path: Path, seed: int) -> list[set[str]]:
    from verimem.community_detector import _load_graph
    g = _load_graph(db_path, "both")
    if g.number_of_nodes() == 0:
        return []
    try:
        comms = nx.algorithms.community.louvain_communities(
            g, weight="weight", seed=int(seed),
        )
    except Exception:  # noqa: BLE001
        return []
    return [{str(n) for n in c} for c in comms]


def _inject_writes(db_path: Path, k: int, inject_seed: int) -> None:
    """Schema-aware injection (from cycle 254 bug-fix)."""
    rng = np.random.default_rng(inject_seed)
    conn = sqlite3.connect(str(db_path))
    try:
        rows = conn.execute(
            "SELECT id, embedding FROM facts "
            "WHERE superseded_by IS NULL AND length(embedding) = 1536"
        ).fetchall()
        if not rows:
            return
        col_info = conn.execute("PRAGMA table_info(facts)").fetchall()
        col_names = {c[1] for c in col_info}
        now = time.time()
        new_facts = []
        for w in range(k):
            anchor_id, anchor_blob = rows[int(rng.integers(0, len(rows)))]
            anchor_emb = np.frombuffer(anchor_blob, dtype=np.float32)
            new_emb = (
                anchor_emb
                + 0.05 * rng.standard_normal(384).astype(np.float32)
            ).astype(np.float32)
            row = {
                "id": f"replinj_{inject_seed}_{now:.0f}_{w}",
                "proposition": f"replicated bench inj {w} seed {inject_seed}",
                "topic": "bench/replicated_injection",
                "confidence": 0.5,
                "source_episodes": "[]",
                "created_at": now,
                "embedding": new_emb.tobytes(),
                "lineage_to": anchor_id,
                "status": "bench_replicated",
            }
            row = {k_: v for k_, v in row.items() if k_ in col_names}
            new_facts.append(row)
        if new_facts:
            cols = list(new_facts[0].keys())
            placeholders = ",".join(["?"] * len(cols))
            sql = (
                f"INSERT OR IGNORE INTO facts "  # noqa: S608
                f"({', '.join(cols)}) VALUES ({placeholders})"
            )
            values = [tuple(row[c] for c in cols) for row in new_facts]
            conn.executemany(sql, values)
        conn.commit()
    finally:
        conn.close()


def run_replicated(
    semantic_db_src: Path,
    k: int,
    n_inject: int,
    n_seed: int,
) -> dict:
    """For each inject_seed, copy fresh DB, inject, compute paired Jaccards
    for each partition seed."""
    seeds = list(range(1, n_seed + 1))
    inject_seeds = list(range(101, 101 + n_inject))
    all_paired: list[dict] = []

    # First, compute baseline once on the ORIGINAL corpus (pristine)
    td_baseline = Path(tempfile.mkdtemp(prefix="replbench_base_"))
    db_baseline = td_baseline / "semantic.db"
    shutil.copy2(semantic_db_src, db_baseline)
    pre_partitions: dict[int, list[set[str]]] = {}
    for s in seeds:
        pre_partitions[s] = _louvain_partition(db_baseline, seed=s)
    baseline_jaccards: list[float] = []
    for i in range(len(seeds)):
        for j in range(i + 1, len(seeds)):
            d = _partition_jaccard(
                pre_partitions[seeds[i]], pre_partitions[seeds[j]],
            )
            baseline_jaccards.append(d)
    shutil.rmtree(td_baseline, ignore_errors=True)

    # For each inject seed, fresh copy + inject + re-Louvain
    for inj_seed in inject_seeds:
        td = Path(tempfile.mkdtemp(prefix=f"replbench_inj{inj_seed}_"))
        db = td / "semantic.db"
        shutil.copy2(semantic_db_src, db)
        _inject_writes(db, k, inj_seed)
        for s in seeds:
            post_part = _louvain_partition(db, seed=s)
            d = _partition_jaccard(pre_partitions[s], post_part)
            all_paired.append({
                "inject_seed": inj_seed,
                "partition_seed": s,
                "delta_j": d,
            })
        shutil.rmtree(td, ignore_errors=True)

    treat_vals = [p["delta_j"] for p in all_paired]
    baseline_mean = float(np.mean(baseline_jaccards)) if baseline_jaccards else 0.0
    treat_mean = float(np.mean(treat_vals)) if treat_vals else 0.0

    # Bootstrap CI of paired effects
    paired_effects = [v - baseline_mean for v in treat_vals]
    if paired_effects:
        rng = np.random.default_rng(42)
        arr = np.array(paired_effects, dtype=np.float64)
        means = [
            float(rng.choice(arr, size=len(arr), replace=True).mean())
            for _ in range(5000)
        ]
        ci_low = float(np.quantile(means, 0.025))
        ci_high = float(np.quantile(means, 0.975))
    else:
        ci_low = ci_high = 0.0

    # Per-inject-seed variance
    by_inject = {}
    for inj_seed in inject_seeds:
        vals = [p["delta_j"] for p in all_paired
                if p["inject_seed"] == inj_seed]
        by_inject[str(inj_seed)] = {
            "mean": float(np.mean(vals)) if vals else 0.0,
            "std": float(np.std(vals)) if vals else 0.0,
            "n": len(vals),
        }

    return {
        "k": k,
        "n_inject": n_inject,
        "n_seed": n_seed,
        "n_paired_total": len(all_paired),
        "baseline_jaccards": baseline_jaccards,
        "baseline_mean": baseline_mean,
        "treat_mean": treat_mean,
        "effect": treat_mean - baseline_mean,
        "bootstrap_ci_95": [ci_low, ci_high],
        "per_inject_seed_stats": by_inject,
        "all_paired_summary": {
            "min": float(min(treat_vals)) if treat_vals else 0.0,
            "max": float(max(treat_vals)) if treat_vals else 0.0,
            "std": float(np.std(treat_vals)) if treat_vals else 0.0,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--semantic-db",
        type=Path,
        default=Path.home() / ".engram" / "semantic" / "semantic.db",
    )
    parser.add_argument("--k", type=int, default=50)
    parser.add_argument("--N-inject", type=int, default=5)
    parser.add_argument("--N-seed", type=int, default=5)
    parser.add_argument("--auto-copy", action="store_true")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    if not args.semantic_db.exists():
        print(f"[error] DB not found: {args.semantic_db}", file=sys.stderr)
        return 1

    print(
        f"[bench] k={args.k} N_inject={args.N_inject} "
        f"N_seed={args.N_seed} ({args.N_inject * args.N_seed} paired)",
        file=sys.stderr,
    )
    result = run_replicated(
        args.semantic_db,
        args.k,
        args.N_inject,
        args.N_seed,
    )
    payload = json.dumps(result, indent=2)
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
        print(f"Wrote {args.output}", file=sys.stderr)
    print(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
