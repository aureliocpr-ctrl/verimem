"""Stress test: N concurrent writer processes on Engram storage layer.

CYCLE #45 (2026-05-14) — transfer of the `nexus-mcp-suite` pattern
(`bench_audit_concurrency.py`: 20 proc × 500 writes × 3 run = 30k entries,
0 loss, 0 corrupt, 560 writes/s under contention, fact 9d7974472be8).

Engram uses SQLite WAL + busy_timeout=10000ms + synchronous=NORMAL. The
expectation is therefore good concurrency under multi-process write load.
This benchmark MEASURES it empirically, on the three storage layers
(`Memory` for episodes, `SemanticStore` for facts, `SkillLibrary` for
skills) instead of trusting docs.

Method:
  1. Create an isolated tmp data dir.
  2. Spawn N=20 subprocess writers, each writes M=500 records into ONE
     of the three stores (hot contention on the same DB).
  3. Wait all, then read the DB from the parent and:
     - count rows → must equal N*M (zero data loss)
     - sample-validate row fields (zero corruption)
     - compute throughput = N*M / wall_time
  4. Repeat 3 times per store-kind; report median.

We bypass embedding for FACT and SKILL stores (they don't call
sentence-transformers on write). For EPISODE store, embedding is
mandatory in `Memory.store()` — we accept the cold-start cost as
realistic baseline (live MCP server eager-preloads the model anyway).

Run:
  python scripts/bench_concurrency.py
  python scripts/bench_concurrency.py --store facts --procs 30 --writes 1000

Result format: JSON to stdout + brief table. Saved to
data/bench_concurrency_<store>.json for diff against future runs.
"""
from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import os
import sqlite3
import statistics
import sys
import tempfile
import time
import uuid
from pathlib import Path

# ---------------------------------------------------------------------------
# Worker functions — each runs in a fresh subprocess (spawn semantics so the
# Memory + embedding are loaded independently and there's no fork-shared
# state. Mimics multiple MCP server invocations writing to the same DB.)
# ---------------------------------------------------------------------------


def _worker_episodes(args: tuple[str, str, int, int]) -> dict:
    """Insert N episode rows; return per-worker metrics."""
    data_dir_str, worker_id, n_writes, base_id = args
    # Force offline mode — avoid HF network roundtrip on subprocess.
    os.environ["HIPPO_OFFLINE"] = "1"
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HIPPO_DATA_DIR"] = data_dir_str
    # CPU-only embedding: prevent 10+ subprocess GPU OOM during stress.
    # Production MCP server is single-process so GPU is fine; bench fails
    # spuriously without this flag because each worker loads MiniLM into
    # CUDA memory and the 10th+ process exhausts the GPU.
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    os.environ["TORCH_USE_CPU"] = "1"

    t_start = time.time()
    from engram.episode import Episode
    from engram.memory import Memory

    mem = Memory(db_path=Path(data_dir_str) / "episodes" / "episodes.db")
    t_init = time.time() - t_start

    t_write_start = time.time()
    errors = []
    for i in range(n_writes):
        try:
            ep = Episode(
                id=uuid.uuid4().hex,
                task_id=f"task-{worker_id}-{i}",
                task_text=f"stress-write proc={worker_id} idx={i}",
                outcome="success",
                final_answer=f"answer {base_id + i}",
                tokens_used=10,
                skills_used=[],
                created_at=time.time(),
            )
            mem.store(ep)
        except Exception as e:
            errors.append({"i": i, "err": f"{type(e).__name__}: {e}"})
    t_write = time.time() - t_write_start
    return {
        "worker_id": worker_id,
        "n_writes": n_writes,
        "n_errors": len(errors),
        "errors_preview": errors[:3],
        "t_init_s": round(t_init, 3),
        "t_write_s": round(t_write, 3),
        "writes_per_sec": round(n_writes / max(t_write, 1e-6), 1),
    }


def _worker_facts(args: tuple[str, str, int, int]) -> dict:
    return _worker_facts_impl(args, id_mode="unique")


def _worker_facts_collision(args: tuple[str, str, int, int]) -> dict:
    """Same as _worker_facts but with DETERMINISTIC shared id space.

    CYCLE #45 critic counterexample (job 134acf1446994a76, worker 'counterexample'
    confidence 0.78): SemanticMemory.store uses `INSERT OR REPLACE INTO facts`
    on `id PRIMARY KEY`. With id collisions across writers, the latest writer
    wins silently — no error, no audit, just data loss.

    This worker uses `id=f"shared-{i:04d}"` instead of uuid4(). Across N
    workers, idx=0 from every worker collides on id="shared-0000". Expected
    final row count: n_writes (NOT n_writes * n_procs). Difference = silent
    overwrites measured empirically.
    """
    return _worker_facts_impl(args, id_mode="collision")


def _worker_facts_impl(
    args: tuple[str, str, int, int],
    id_mode: str = "unique",
) -> dict:
    data_dir_str, worker_id, n_writes, base_id = args
    os.environ["HIPPO_OFFLINE"] = "1"
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HIPPO_DATA_DIR"] = data_dir_str
    # CPU-only embedding: prevent 10+ subprocess GPU OOM during stress.
    # Production MCP server is single-process so GPU is fine; bench fails
    # spuriously without this flag because each worker loads MiniLM into
    # CUDA memory and the 10th+ process exhausts the GPU.
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    os.environ["TORCH_USE_CPU"] = "1"

    t_start = time.time()
    from engram.semantic import Fact, SemanticMemory

    store = SemanticMemory(db_path=Path(data_dir_str) / "semantic" / "semantic.db")
    t_init = time.time() - t_start

    t_write_start = time.time()
    errors = []
    for i in range(n_writes):
        try:
            kwargs = dict(
                proposition=f"stress-fact proc={worker_id} idx={i}",
                topic=f"bench/concurrency/{worker_id}",
                confidence=0.9,
            )
            if id_mode == "collision":
                # Shared id-space: all workers will write to the same N ids.
                kwargs["id"] = f"shared-{i:04d}"
            store.store(Fact(**kwargs))
        except Exception as e:
            errors.append({"i": i, "err": f"{type(e).__name__}: {e}"})
    t_write = time.time() - t_write_start
    return {
        "worker_id": worker_id,
        "n_writes": n_writes,
        "n_errors": len(errors),
        "errors_preview": errors[:3],
        "t_init_s": round(t_init, 3),
        "t_write_s": round(t_write, 3),
        "writes_per_sec": round(n_writes / max(t_write, 1e-6), 1),
    }


# ---------------------------------------------------------------------------
# Bench driver
# ---------------------------------------------------------------------------


def _verify_rows(
    db_path: Path,
    table: str,
    *,
    content_validate: bool = False,
    sample_size: int = 200,
) -> tuple[int, list[str]]:
    """Return (row_count, list_of_corruption_findings).

    Cycle #47 (2026-05-14, critic counterexample 134acf1446994a76): the
    previous version only checked `count(*)` and `PRAGMA integrity_check`
    (page-level). A swap-fields corruption (e.g., proposition of worker
    A landing in row of worker B) passes both checks. With
    `content_validate=True`, sample-validate `sample_size` random rows:
    for the `facts` table we expect the proposition to match the schema
    `stress-fact proc=(\\w+) idx=(\\d+)` and the topic to be
    `bench/concurrency/{worker_id}` — if topic doesn't match the
    proposition's `proc` value, that's a swap-field corruption.

    For other tables this is a no-op (returns count + integrity_check
    only).
    """
    import re
    conn = sqlite3.connect(str(db_path), timeout=10.0)
    try:
        rows = conn.execute(f"SELECT count(*) FROM {table}").fetchone()
        n = int(rows[0]) if rows else 0
        # Sanity check: integrity_check pragma
        integrity = conn.execute("PRAGMA integrity_check").fetchone()
        integ_ok = integrity[0] == "ok" if integrity else False
        findings: list[str] = []
        if not integ_ok:
            findings.append(f"integrity_check failed: {integrity}")

        if content_validate and table == "facts" and n > 0:
            # Sample N random rows for swap-field detection.
            k = min(sample_size, n)
            sample_rows = conn.execute(
                f"SELECT proposition, topic FROM {table} "
                f"ORDER BY RANDOM() LIMIT ?",
                (k,),
            ).fetchall()
            pat = re.compile(r"^stress-fact proc=(\w+) idx=(\d+)$")
            for prop, topic in sample_rows:
                m = pat.match(prop or "")
                if not m:
                    findings.append(
                        f"unparseable proposition (corruption?): {prop[:60]!r}"
                    )
                    continue
                proc_id = m.group(1)
                expected_topic = f"bench/concurrency/{proc_id}"
                if topic != expected_topic:
                    findings.append(
                        f"swap-field corruption: proposition says "
                        f"proc={proc_id}, topic says {topic} "
                        f"(expected {expected_topic})"
                    )
            # Cap findings to keep report readable
            if len(findings) > 10:
                findings = findings[:10] + [f"... +{len(findings)-10} more"]
        return n, findings
    finally:
        conn.close()


def run_bench(
    store_kind: str = "episodes",
    n_procs: int = 20,
    n_writes: int = 500,
    n_runs: int = 3,
) -> dict:
    """Run the bench n_runs times, returning aggregated stats."""
    worker_fn = {
        "episodes": _worker_episodes,
        "facts": _worker_facts,
        "facts_collision": _worker_facts_collision,
    }[store_kind]

    db_path_table = {
        "episodes": ("episodes/episodes.db", "episodes"),
        "facts":    ("semantic/semantic.db", "facts"),
        "facts_collision": ("semantic/semantic.db", "facts"),
    }[store_kind]

    runs: list[dict] = []
    for run_idx in range(n_runs):
        tmp_root = Path(tempfile.mkdtemp(prefix=f"engram-bench-{store_kind}-"))
        try:
            args = [
                (str(tmp_root), f"w{wid}", n_writes, wid * n_writes)
                for wid in range(n_procs)
            ]
            t0 = time.time()
            with mp.get_context("spawn").Pool(processes=n_procs) as pool:
                results = pool.map(worker_fn, args)
            wall_s = time.time() - t0

            # Verify
            sub, table = db_path_table
            db_path = tmp_root / sub
            # Cycle #47: enable content validation by default for facts/
            # facts_collision modes (where the propositions follow a known
            # schema we can validate).
            n_rows, corruption = _verify_rows(
                db_path, table,
                content_validate=(store_kind in ("facts", "facts_collision")),
            )
            n_expected = n_procs * n_writes
            n_errors_total = sum(r["n_errors"] for r in results)

            runs.append({
                "run_idx": run_idx,
                "wall_s": round(wall_s, 3),
                "throughput_wps": round(n_expected / wall_s, 1),
                "n_expected": n_expected,
                "n_rows_in_db": n_rows,
                "n_loss": n_expected - n_rows,
                "n_worker_errors": n_errors_total,
                "corruption": corruption,
                "per_worker_avg_wps": round(
                    statistics.mean(r["writes_per_sec"] for r in results), 1
                ),
                "per_worker_avg_init_s": round(
                    statistics.mean(r["t_init_s"] for r in results), 3
                ),
                "worker_errors_preview": [
                    e for r in results for e in r["errors_preview"]
                ][:5],
            })
        finally:
            # Clean tmp tree
            import shutil
            shutil.rmtree(tmp_root, ignore_errors=True)

    # Aggregate
    losses = [r["n_loss"] for r in runs]
    corruptions = [c for r in runs for c in r["corruption"]]
    return {
        "store_kind": store_kind,
        "n_procs": n_procs,
        "n_writes_per_proc": n_writes,
        "n_runs": n_runs,
        "total_writes_per_run": n_procs * n_writes,
        "runs": runs,
        "summary": {
            "median_wall_s": round(statistics.median(r["wall_s"] for r in runs), 3),
            "median_throughput_wps": round(
                statistics.median(r["throughput_wps"] for r in runs), 1
            ),
            "max_loss": max(losses),
            "total_loss": sum(losses),
            "all_corruption_findings": corruptions,
            "all_runs_clean": (
                max(losses) == 0
                and len(corruptions) == 0
                and all(r["n_worker_errors"] == 0 for r in runs)
            ),
        },
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--store", choices=["episodes", "facts", "facts_collision"], default="facts")
    p.add_argument("--procs", type=int, default=20)
    p.add_argument("--writes", type=int, default=500)
    p.add_argument("--runs", type=int, default=3)
    p.add_argument("--out", default=None,
                   help="JSON output file (default: data/bench_concurrency_<store>.json)")
    args = p.parse_args(argv)

    print("=== Engram concurrency bench ===")
    print(f"  store: {args.store}, procs: {args.procs}, "
          f"writes/proc: {args.writes}, runs: {args.runs}")
    print(f"  expected total: {args.procs * args.writes * args.runs} rows")
    print()

    result = run_bench(
        store_kind=args.store,
        n_procs=args.procs,
        n_writes=args.writes,
        n_runs=args.runs,
    )

    out_path = Path(args.out) if args.out else Path(
        f"data/bench_concurrency_{args.store}.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

    s = result["summary"]
    print("=== RESULTS ===")
    print(f"  median wall:       {s['median_wall_s']}s")
    print(f"  median throughput: {s['median_throughput_wps']} writes/s")
    print(f"  total loss:        {s['total_loss']} (across {args.runs} runs)")
    print(f"  corruption:        {len(s['all_corruption_findings'])}")
    print(f"  CLEAN VERDICT:     {s['all_runs_clean']}")
    print(f"  full report:       {out_path}")

    return 0 if s["all_runs_clean"] else 1


if __name__ == "__main__":
    sys.exit(main())
