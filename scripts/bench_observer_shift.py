"""Cycle 253 (2026-05-23) — Structural Observer-Shift bench.

Measures the Jaccard distance between Louvain partition assignments
pre/post self-writes, vs the stochastic baseline (different seeds on
identical corpus).

Falsifiable claim (paper §3.6):
    H_0: E = Delta_treatment - Delta_baseline <= 0.05
    H_1: E > 0.05 with CI 95% lower bound > 0

Usage:
    python -m scripts.bench_observer_shift \\
        --semantic-db ~/.engram/semantic/semantic.db \\
        --N 5 --k 50 --output results.json

Output JSON schema:
    {
      "n_seeds": int,
      "k_writes": int,
      "n_facts_pre": int,
      "n_facts_post": int,
      "baseline_jaccards": [float, ...],   # pairwise on same graph
      "treatment_jaccards": [float, ...],  # paired pre/post per seed
      "baseline_mean": float,
      "treatment_mean": float,
      "effect": float,                     # treatment - baseline
      "bootstrap_ci_95": [low, high],
      "verdict": "H1_supported" | "H0_supported" | "inconclusive"
    }

Defensive: missing DB / Louvain error → partial results with warnings.
A4 onesto: synthetic mode (--synthetic) runs with seeded synthetic
corpus when real corpus unavailable; clearly flagged in output.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from pathlib import Path

import networkx as nx
import numpy as np


def _partition_jaccard(p1: list[set[str]], p2: list[set[str]]) -> float:
    """Jaccard distance between two partitions over node-pair co-clustering.

    Δ_J(P1, P2) = 1 - |co-clustered in both| / |co-clustered in either|

    Returns 0.0 when both partitions agree on all node pairs (identical),
    and 1.0 when no pair is co-clustered in both.
    """
    # All nodes appearing in p1 OR p2.
    all_nodes: set[str] = set()
    for c in p1:
        all_nodes.update(c)
    for c in p2:
        all_nodes.update(c)
    nodes = sorted(all_nodes)
    if len(nodes) < 2:
        return 0.0

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
    inter = pairs_1 & pairs_2
    union = pairs_1 | pairs_2
    if not union:
        return 0.0
    return 1.0 - (len(inter) / len(union))


def _build_synthetic_db(db_path: Path, n_facts: int = 200,
                        n_clusters: int = 8) -> None:
    """Build a synthetic semantic.db for bench reproducibility.

    Topology: ``n_clusters`` mini-cliques of size ``n_facts/n_clusters``,
    plus a few random cross-cluster edges. Embeddings: per-cluster
    centroids with Gaussian noise.
    """
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS facts (
                id TEXT PRIMARY KEY, topic TEXT, proposition TEXT,
                embedding BLOB, lineage_to TEXT, superseded_by TEXT, status TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS causal_edges (
                src TEXT, dst TEXT, weight REAL
            )
        """)
        rng = np.random.default_rng(7)
        per_cluster = n_facts // n_clusters
        for c in range(n_clusters):
            base = np.zeros(384, dtype=np.float32)
            base[(c * 17) % 384] = 1.0
            for i in range(per_cluster):
                fid = f"f_{c}_{i}"
                emb = base + 0.08 * rng.standard_normal(384).astype(np.float32)
                parent = f"f_{c}_{i-1}" if i > 0 else None
                conn.execute(
                    "INSERT INTO facts (id, topic, proposition, embedding, "
                    "lineage_to, status) VALUES (?, ?, ?, ?, ?, ?)",
                    (fid, f"p/c{c}", f"f{c}_{i}", emb.tobytes(),
                     parent, None),
                )
            # intra-cluster causal edges (clique partial)
            for i in range(per_cluster):
                for j in range(i + 1, per_cluster):
                    if rng.random() < 0.6:
                        conn.execute(
                            "INSERT INTO causal_edges (src, dst, weight) "
                            "VALUES (?, ?, ?)",
                            (f"f_{c}_{i}", f"f_{c}_{j}", 1.0),
                        )
        # Cross-cluster sparse edges
        for _ in range(n_facts // 4):
            c1 = int(rng.integers(0, n_clusters))
            c2 = int(rng.integers(0, n_clusters))
            if c1 == c2:
                continue
            i = int(rng.integers(0, per_cluster))
            j = int(rng.integers(0, per_cluster))
            conn.execute(
                "INSERT INTO causal_edges (src, dst, weight) VALUES (?, ?, ?)",
                (f"f_{c1}_{i}", f"f_{c2}_{j}", 1.0),
            )
        conn.commit()
    finally:
        conn.close()


def _inject_writes(db_path: Path, k: int, *, seed: int = 99) -> None:
    """Inject k synthetic facts targeting random existing clusters.

    Each new fact points its lineage_to at a random existing fact and
    inherits a noisy version of its embedding. This simulates the
    Auto-Dream "stuck-list seed + community-hook" write pattern.

    Schema-aware: uses PRAGMA table_info to discover NOT NULL columns
    and supplies safe defaults so the INSERT does not silently fail
    on production schema with additional constraints.
    """
    rng = np.random.default_rng(seed)
    conn = sqlite3.connect(str(db_path))
    try:
        rows = conn.execute(
            "SELECT id, embedding FROM facts WHERE superseded_by IS NULL "
            "AND length(embedding) = 1536"
        ).fetchall()
        if not rows:
            return
        # Schema discovery: get all columns in facts table.
        col_info = conn.execute("PRAGMA table_info(facts)").fetchall()
        col_names = {c[1] for c in col_info}
        now = time.time()
        new_facts = []
        for w in range(k):
            anchor_idx = int(rng.integers(0, len(rows)))
            anchor_id, anchor_blob = rows[anchor_idx]
            anchor_emb = np.frombuffer(anchor_blob, dtype=np.float32)
            new_emb = (
                anchor_emb
                + 0.05 * rng.standard_normal(384).astype(np.float32)
            ).astype(np.float32)
            new_fact_id = f"bench_inject_{seed}_{now:.0f}_{w}"
            # Build row dict with all required columns
            row = {
                "id": new_fact_id,
                "proposition": f"bench-injected fact {w}",
                "topic": "bench/observer_shift/injected",
                "confidence": 0.5,
                "source_episodes": "[]",
                "created_at": now,
                "embedding": new_emb.tobytes(),
                "lineage_to": anchor_id,
                "status": "bench_injected",
            }
            # Only keep keys that exist in the schema (forward-compat).
            row = {k_: v for k_, v in row.items() if k_ in col_names}
            new_facts.append(row)
        # Build INSERT dynamically from the first row's keys.
        if new_facts:
            cols = list(new_facts[0].keys())
            placeholders = ",".join(["?"] * len(cols))
            sql = (  # noqa: S608 - cols are validated against schema
                f"INSERT OR IGNORE INTO facts "
                f"({', '.join(cols)}) VALUES ({placeholders})"
            )
            values = [tuple(row[c] for c in cols) for row in new_facts]
            conn.executemany(sql, values)
        conn.commit()
    finally:
        conn.close()


def _louvain_partition(
    db_path: Path, seed: int,
) -> list[set[str]]:
    """Single Louvain run, returns list of node-id sets.

    Imports ``community_detector`` lazily to avoid circular import in
    bench-only usage.
    """
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


def _emerging_skills_set(
    db_path: Path, *, n_facts: int, enable_second_pass: bool = False,
) -> set[str]:
    """Run detect_emerging_skills with adaptive thresholds. Returns set
    of suggested_skill_name (proxy for emergence candidate identity).

    Args:
        enable_second_pass: when True, route through the cycle 253
            architectural cure (now wired in cycle 260). When False
            (default), legacy single-pass Louvain.

    Adaptive thresholds (cycle 248-249) auto-scale by corpus size; the
    cycle 233 static defaults (0.4/0.2) produce zero candidates on
    corpora > 1500 facts. Using adaptive ensures the downstream bench
    is comparable to the production Auto-Dream pipeline behaviour.
    """
    from verimem.adaptive_threshold import adaptive_thresholds
    from verimem.skill_emergence_detector import detect_emerging_skills

    purity, cohesion = adaptive_thresholds(n_facts)
    candidates = detect_emerging_skills(
        db_path,
        min_community_size=4,
        min_topic_purity=purity,
        min_cohesion=cohesion,
        max_n=50,
        seed=42,
        enable_second_pass=enable_second_pass,
    )
    return {
        c.get("suggested_skill_name", "")
        for c in candidates
        if c.get("suggested_skill_name")
    }


def _set_jaccard_distance(a: set[str], b: set[str]) -> float:
    """1 - |A ∩ B| / |A ∪ B|. Returns 0.0 when both empty."""
    if not a and not b:
        return 0.0
    union = a | b
    if not union:
        return 0.0
    return 1.0 - (len(a & b) / len(union))


def _bootstrap_ci(values: list[float], n_resamples: int = 10_000,
                  confidence: float = 0.95,
                  rng_seed: int = 42) -> tuple[float, float]:
    """Bootstrap 95% CI of the mean."""
    if not values:
        return (0.0, 0.0)
    rng = np.random.default_rng(rng_seed)
    arr = np.array(values, dtype=np.float64)
    means = []
    for _ in range(n_resamples):
        sample = rng.choice(arr, size=len(arr), replace=True)
        means.append(float(sample.mean()))
    alpha = (1.0 - confidence) / 2.0
    low = float(np.quantile(means, alpha))
    high = float(np.quantile(means, 1.0 - alpha))
    return (low, high)


def run_bench(
    semantic_db: Path,
    n_seeds: int = 5,
    k_writes: int = 50,
    effect_threshold: float = 0.05,
    measure_emergence: bool = False,
    enable_second_pass: bool = False,
) -> dict:
    """Run the full observer-shift bench.

    Args:
        measure_emergence: when True, ALSO compute emerging-skill
            candidate set Jaccard distance pre/post writes (downstream
            consequence measurement for paper §5.6).
    """
    if not semantic_db.exists():
        return {"error": f"DB not found: {semantic_db}", "verdict": "error"}

    conn = sqlite3.connect(str(semantic_db))
    try:
        n_facts_pre = conn.execute(
            "SELECT COUNT(*) FROM facts WHERE superseded_by IS NULL"
        ).fetchone()[0]
    finally:
        conn.close()

    seeds = list(range(1, n_seeds + 1))
    t_start = time.time()

    # Optional: pre-write emerging-skill candidate snapshot
    emerging_pre: set[str] = set()
    if measure_emergence:
        emerging_pre = _emerging_skills_set(
            semantic_db,
            n_facts=n_facts_pre,
            enable_second_pass=enable_second_pass,
        )

    # Phase 1: Baseline (different seeds, same graph)
    pre_partitions: dict[int, list[set[str]]] = {}
    for s in seeds:
        pre_partitions[s] = _louvain_partition(semantic_db, seed=s)
    baseline_jaccards: list[float] = []
    for i in range(len(seeds)):
        for j in range(i + 1, len(seeds)):
            d = _partition_jaccard(pre_partitions[seeds[i]],
                                    pre_partitions[seeds[j]])
            baseline_jaccards.append(d)

    # Phase 2: Inject writes, then re-run with same seeds
    _inject_writes(semantic_db, k_writes, seed=99)
    conn = sqlite3.connect(str(semantic_db))
    try:
        n_facts_post = conn.execute(
            "SELECT COUNT(*) FROM facts WHERE superseded_by IS NULL"
        ).fetchone()[0]
    finally:
        conn.close()
    post_partitions: dict[int, list[set[str]]] = {}
    for s in seeds:
        post_partitions[s] = _louvain_partition(semantic_db, seed=s)
    treatment_jaccards: list[float] = []
    for s in seeds:
        d = _partition_jaccard(pre_partitions[s], post_partitions[s])
        treatment_jaccards.append(d)

    # Optional: post-write emerging-skill candidate snapshot + Jaccard
    emerging_post: set[str] = set()
    emerging_jaccard: float | None = None
    if measure_emergence:
        emerging_post = _emerging_skills_set(
            semantic_db,
            n_facts=n_facts_post,
            enable_second_pass=enable_second_pass,
        )
        emerging_jaccard = _set_jaccard_distance(emerging_pre, emerging_post)

    baseline_mean = (
        float(np.mean(baseline_jaccards)) if baseline_jaccards else 0.0
    )
    treatment_mean = (
        float(np.mean(treatment_jaccards)) if treatment_jaccards else 0.0
    )
    effect = treatment_mean - baseline_mean

    # Bootstrap CI of the effect using paired resampling.
    paired_effects = [
        t - baseline_mean for t in treatment_jaccards
    ] if treatment_jaccards else []
    ci_low, ci_high = _bootstrap_ci(paired_effects)

    if ci_low > 0 and effect > effect_threshold:
        verdict = "H1_supported"
    elif ci_high <= effect_threshold:
        verdict = "H0_supported"
    else:
        verdict = "inconclusive"

    result = {
        "n_seeds": int(n_seeds),
        "k_writes": int(k_writes),
        "n_facts_pre": int(n_facts_pre),
        "n_facts_post": int(n_facts_post),
        "baseline_jaccards": baseline_jaccards,
        "treatment_jaccards": treatment_jaccards,
        "baseline_mean": float(baseline_mean),
        "treatment_mean": float(treatment_mean),
        "effect": float(effect),
        "bootstrap_ci_95": [float(ci_low), float(ci_high)],
        "effect_threshold": float(effect_threshold),
        "verdict": verdict,
        "elapsed_s": float(time.time() - t_start),
    }
    if measure_emergence:
        result["emerging_pre_count"] = len(emerging_pre)
        result["emerging_post_count"] = len(emerging_post)
        result["emerging_pre_names"] = sorted(emerging_pre)
        result["emerging_post_names"] = sorted(emerging_post)
        result["emerging_jaccard"] = float(emerging_jaccard or 0.0)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--semantic-db",
        type=Path,
        default=Path.home() / ".engram" / "semantic" / "semantic.db",
        help="Path to semantic.db (default: ~/.engram/semantic/semantic.db)",
    )
    parser.add_argument("--N", type=int, default=5, dest="n_seeds")
    parser.add_argument("--k", type=int, default=50, dest="k_writes")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument(
        "--synthetic",
        action="store_true",
        help="Use synthetic seeded corpus instead of real DB (reproducible)",
    )
    parser.add_argument(
        "--auto-copy",
        action="store_true",
        help="Copy production DB to tempdir before running (safe — never "
             "modifies the source DB). Recommended for --semantic-db pointing "
             "at production ~/.engram/semantic/semantic.db.",
    )
    parser.add_argument(
        "--measure-emergence",
        action="store_true",
        help="Also compute Jaccard distance on emerging-skill candidate "
             "sets pre/post writes (paper §5.6 downstream consequence).",
    )
    parser.add_argument(
        "--enable-second-pass",
        action="store_true",
        help="Route emergence detection through second_pass_louvain cure "
             "(cycle 260 wired). Validates whether the cure reduces the "
             "observer-shift effect on downstream emergence pipeline.",
    )
    args = parser.parse_args()

    cleanup_dir: Path | None = None
    if args.synthetic:
        import tempfile
        td = tempfile.mkdtemp(prefix="engram_bench_")
        cleanup_dir = Path(td)
        db = cleanup_dir / "semantic.db"
        _build_synthetic_db(db, n_facts=200, n_clusters=8)
        print(f"[synthetic] DB at {db}", file=sys.stderr)
        semantic_db = db
        mode = "synthetic"
    elif args.auto_copy:
        import shutil
        import tempfile
        if not args.semantic_db.exists():
            print(f"[error] DB not found: {args.semantic_db}", file=sys.stderr)
            return 1
        td = tempfile.mkdtemp(prefix="engram_bench_safecopy_")
        cleanup_dir = Path(td)
        db = cleanup_dir / "semantic.db"
        shutil.copy2(args.semantic_db, db)
        print(
            f"[auto-copy] Copied {args.semantic_db} -> {db} "
            f"({db.stat().st_size} bytes)",
            file=sys.stderr,
        )
        semantic_db = db
        mode = "production_safecopy"
    else:
        semantic_db = args.semantic_db
        mode = "production_inplace"  # WARNING: modifies source DB

    try:
        result = run_bench(
            semantic_db,
            n_seeds=args.n_seeds,
            k_writes=args.k_writes,
            measure_emergence=args.measure_emergence,
            enable_second_pass=args.enable_second_pass,
        )
    finally:
        if cleanup_dir is not None and cleanup_dir.exists():
            try:
                import shutil
                shutil.rmtree(cleanup_dir, ignore_errors=True)
                print(f"[cleanup] removed {cleanup_dir}", file=sys.stderr)
            except Exception:  # noqa: BLE001
                pass

    result["mode"] = mode
    payload = json.dumps(result, indent=2)
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
        print(f"Wrote {args.output}", file=sys.stderr)
    print(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
