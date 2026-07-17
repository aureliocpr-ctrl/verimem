"""Cycle 381 bench — SOS-COMPENSATING WRITES falsifiable contract.

Compare vanilla random anchor vs compensated anchor selection:
  ΔJ_compensated < ΔJ_vanilla / 2 → SUPPORTED
  Otherwise → FALSIFIED, accept honest negative result.

Protocol:
  1. Safe-copy production semantic.db
  2. Compute pre-write Louvain partition (seed=42)
  3. Inject k=50 writes with VANILLA random anchors
  4. Compute post-write partition (same seed=42)
  5. ΔJ_vanilla = partition_jaccard(pre, post)
  Repeat with COMPENSATED anchors:
  6. Safe-copy AGAIN production (fresh state)
  7. Inject k=50 writes selecting compensated anchor each time
  8. ΔJ_compensated = partition_jaccard(pre, post)
  9. Report ratio + verdict

Usage:
    python -m scripts.bench_sos_compensator --k 50 --N 5
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

import numpy as np


def _inject_one(db_path: Path, anchor_id: str, suffix: str) -> None:
    """Insert a single fact attached to anchor."""
    # Use stable hash of suffix as deterministic seed (avoid parsing)
    import hashlib as _hl
    seed_int = int(_hl.sha256(suffix.encode()).hexdigest()[:8], 16)
    rng = np.random.default_rng(seed_int)
    conn = sqlite3.connect(str(db_path))
    try:
        col_info = conn.execute("PRAGMA table_info(facts)").fetchall()
        col_names = {c[1] for c in col_info}
        # Get anchor's embedding for noisy inheritance
        row = conn.execute(
            "SELECT embedding FROM facts WHERE id = ?", (anchor_id,),
        ).fetchone()
        if row is None or row[0] is None:
            base_emb = rng.standard_normal(384).astype(np.float32)
        else:
            anchor_blob = row[0]
            if len(anchor_blob) == 1536:
                anchor_emb = np.frombuffer(anchor_blob, dtype=np.float32)
                base_emb = (
                    anchor_emb
                    + 0.05 * rng.standard_normal(384).astype(np.float32)
                ).astype(np.float32)
            else:
                base_emb = rng.standard_normal(384).astype(np.float32)
        new_emb = base_emb / max(float(np.linalg.norm(base_emb)), 1e-9)
        fid = f"bench_compensator_{suffix}"
        row_data = {
            "id": fid, "proposition": f"compensator inject {suffix}",
            "topic": "bench/sos_compensator/injected",
            "confidence": 0.5, "source_episodes": "[]",
            "created_at": time.time(),
            "embedding": new_emb.astype(np.float32).tobytes(),
            "lineage_to": anchor_id, "status": "bench_compensator",
        }
        row_data = {k: v for k, v in row_data.items() if k in col_names}
        cols = list(row_data.keys())
        placeholders = ",".join(["?"] * len(cols))
        conn.execute(
            f"INSERT OR IGNORE INTO facts ({', '.join(cols)}) "
            f"VALUES ({placeholders})",  # noqa: S608
            tuple(row_data[c] for c in cols),
        )
        conn.commit()
    finally:
        conn.close()


def _partition_jaccard(p1: list[set[str]], p2: list[set[str]]) -> float:
    all_nodes: set[str] = set()
    for c in p1:
        all_nodes.update(c)
    for c in p2:
        all_nodes.update(c)
    if len(all_nodes) < 2:
        return 0.0

    def co_pairs(part):
        out = set()
        for c in part:
            mem = sorted(c)
            for i in range(len(mem)):
                for j in range(i + 1, len(mem)):
                    out.add(frozenset({mem[i], mem[j]}))
        return out
    p1p = co_pairs(p1)
    p2p = co_pairs(p2)
    inter = p1p & p2p
    union = p1p | p2p
    if not union:
        return 0.0
    return 1.0 - (len(inter) / len(union))


def _louvain(db: Path, seed: int = 42) -> list[set[str]]:
    import networkx as nx

    from verimem.community_detector import _load_graph
    g = _load_graph(db, "both")
    if g.number_of_nodes() == 0:
        return []
    comms = nx.algorithms.community.louvain_communities(
        g, weight="weight", seed=seed,
    )
    return [{str(n) for n in c} for c in comms]


def run_one_arm(src: Path, k: int, mode: str, n_seed: int = 0) -> dict:
    """One arm: copy DB, inject k facts in mode, measure ΔJ."""
    from verimem.sos_compensator import (
        select_compensated_anchor,
        select_vanilla_anchor,
    )
    tmp_dir = Path(tempfile.mkdtemp(prefix=f"bench_compensator_{mode}_"))
    try:
        db = tmp_dir / "s.db"
        shutil.copy2(src, db)
        pre = _louvain(db, seed=42)
        for i in range(k):
            sel_seed = n_seed * 1000 + i
            if mode == "vanilla":
                sel = select_vanilla_anchor(db, rng_seed=sel_seed)
            elif mode == "compensated":
                sel = select_compensated_anchor(
                    db, k_candidates=20, rng_seed=sel_seed,
                )
            else:
                raise ValueError(mode)
            if not sel.get("anchor_id"):
                continue
            _inject_one(db, sel["anchor_id"], f"inj{sel_seed:05d}_{mode}")
        post = _louvain(db, seed=42)
        delta = _partition_jaccard(pre, post)
        return {
            "mode": mode, "k": k, "delta_jaccard": delta,
            "n_pre_communities": len(pre),
            "n_post_communities": len(post),
        }
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--semantic-db", type=Path,
                        default=Path.home() / ".engram" / "semantic" / "semantic.db")
    parser.add_argument("--k", type=int, default=50)
    parser.add_argument("--N", type=int, default=3)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    if not args.semantic_db.exists():
        print(f"[error] db not found: {args.semantic_db}", file=sys.stderr)
        return 1

    t_start = time.time()
    vanilla_results: list[float] = []
    compensated_results: list[float] = []

    for n in range(args.N):
        print(f"[run] n={n}/{args.N}...", file=sys.stderr)
        rv = run_one_arm(args.semantic_db, args.k, "vanilla", n_seed=n)
        rc = run_one_arm(args.semantic_db, args.k, "compensated", n_seed=n)
        vanilla_results.append(rv["delta_jaccard"])
        compensated_results.append(rc["delta_jaccard"])
        print(f"  vanilla={rv['delta_jaccard']:.4f} "
              f"compensated={rc['delta_jaccard']:.4f}", file=sys.stderr)

    v_mean = sum(vanilla_results) / len(vanilla_results)
    c_mean = sum(compensated_results) / len(compensated_results)
    ratio = c_mean / v_mean if v_mean > 0 else float("inf")

    # Falsifiable verdict: c_mean < v_mean / 2 → supported
    if c_mean < v_mean / 2:
        verdict = "supported_strong (ΔJ_comp < ΔJ_vanilla/2)"
    elif c_mean < v_mean:
        verdict = "supported_weak (ΔJ_comp < ΔJ_vanilla but not /2)"
    elif c_mean == v_mean:
        verdict = "equivalent"
    else:
        verdict = "falsified (ΔJ_comp >= ΔJ_vanilla)"

    payload = {
        "k_writes": args.k, "N_runs": args.N,
        "vanilla_delta_jaccards": vanilla_results,
        "compensated_delta_jaccards": compensated_results,
        "vanilla_mean": v_mean,
        "compensated_mean": c_mean,
        "ratio": ratio,
        "verdict": verdict,
        "elapsed_s": time.time() - t_start,
    }
    text = json.dumps(payload, indent=2)
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
