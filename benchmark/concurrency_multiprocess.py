"""Multi-PROCESS concurrency stress — the real 'N Claude instances share one
store' question, not the GIL-pessimistic thread version.

Yesterday's thread harness proved SQLite never corrupts under contention but
could not reproduce the 60s hangs seen in the live mcp_audit.log (threads
serialize the CPU work under the GIL, so they neither parallelize numpy nor
reproduce the process-level lock contention). This spawns SEPARATE PROCESSES —
each its own Memory + its own SQLite connection — exactly like N MCP servers on
one semantic.db, and reports the tail that matters: p99 and MAX latency, plus
how many ops crossed the 'the client gave up' thresholds (>5s, >10s).

The number this answers: 'verimem non andava per 2 istanze contemporaneamente'.

    python -m benchmark.concurrency_multiprocess --workers 2 5 --secs 15
"""
from __future__ import annotations

import argparse
import multiprocessing as mp
import os
import time
from pathlib import Path


def _pctl(xs: list[float], p: float) -> float:
    if not xs:
        return 0.0
    xs = sorted(xs)
    i = min(len(xs) - 1, int(round(p / 100.0 * (len(xs) - 1))))
    return round(xs[i] * 1000, 1)  # ms


def _worker(db_path: str, secs: float, wid: int, q: mp.Queue) -> None:
    """One process = one client. Own Memory, own connection. Mixed read/write
    for `secs` seconds; every op's latency and every error is recorded."""
    # keep each worker single-threaded on the CPU side so the measurement is
    # about the STORE's concurrency, not numpy thread oversubscription
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    # quiet the store's own logging: N processes interleaving stdout otherwise
    # shreds the result table (and floods the pipe).
    import logging
    logging.disable(logging.CRITICAL)
    from verimem.client import Memory
    m = Memory(Path(db_path))
    reads: list[float] = []
    writes: list[float] = []
    errors: list[str] = []
    n = 0
    stop = time.time() + secs
    while time.time() < stop:
        n += 1
        # 3 reads : 1 write, the shape of an interactive assistant session
        if n % 4 == 0:
            t0 = time.perf_counter()
            try:
                m.add(f"Worker {wid} observation {n}: subsystem {n % 7} "
                      f"changed state at tick {n}.", topic=f"w{wid}/obs")
                writes.append(time.perf_counter() - t0)
            except Exception as exc:  # noqa: BLE001 — surfaced, never hidden
                errors.append(f"write:{type(exc).__name__}:{exc}"[:120])
        else:
            t0 = time.perf_counter()
            try:
                list(m.search(f"subsystem {n % 7} state", k=5))
                reads.append(time.perf_counter() - t0)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"read:{type(exc).__name__}:{exc}"[:120])
    q.put({"wid": wid, "reads": reads, "writes": writes, "errors": errors})


def _seed(db_path: Path, n: int = 40) -> None:
    from verimem.client import Memory
    m = Memory(db_path)
    for i in range(n):
        m.add(f"Seed {i}: subsystem {i % 7} handles the nominal case {i}.",
              topic=f"seed/{i % 5}")


def run(n_workers: int, secs: float, db_path: Path) -> dict:
    ctx = mp.get_context("spawn")   # Windows-safe; matches real separate procs
    q: mp.Queue = ctx.Queue()
    procs = [ctx.Process(target=_worker, args=(str(db_path), secs, w, q))
             for w in range(n_workers)]
    t0 = time.perf_counter()
    for p in procs:
        p.start()
    results = [q.get() for _ in procs]   # drain before join (avoids pipe stall)
    for p in procs:
        p.join()
    wall = time.perf_counter() - t0

    reads = [x for r in results for x in r["reads"]]
    writes = [x for r in results for x in r["writes"]]
    errors = [e for r in results for e in r["errors"]]
    allops = reads + writes
    over5 = sum(1 for x in allops if x > 5.0)
    over10 = sum(1 for x in allops if x > 10.0)
    return {
        "workers": n_workers,
        "wall_s": round(wall, 1),
        "n_reads": len(reads), "n_writes": len(writes), "n_errors": len(errors),
        "read_p50": _pctl(reads, 50), "read_p99": _pctl(reads, 99),
        "read_max": _pctl(reads, 100),
        "write_p50": _pctl(writes, 50), "write_p99": _pctl(writes, 99),
        "write_max": _pctl(writes, 100),
        "ops_over_5s": over5, "ops_over_10s": over10,
        "throughput_ops_s": round(len(allops) / wall, 1) if wall else 0.0,
        "error_samples": errors[:5],
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, nargs="+", default=[2, 5])
    ap.add_argument("--secs", type=float, default=15.0)
    ap.add_argument("--json", dest="json_out")
    args = ap.parse_args()

    import shutil
    import tempfile
    base = Path(tempfile.mkdtemp(prefix="verimem_mp_"))
    db = base / "shared.db"
    _seed(db)
    bt = os.environ.get("ENGRAM_BUSY_TIMEOUT_MS", "(default 60000)")
    all_rows = []
    print("multi-process concurrency — ONE store, N separate processes")
    print(f"  busy_timeout = {bt}")
    print(f"  {'N':>2}  {'reads':>6} {'writes':>6} {'err':>4}  "
          f"{'r_p50':>6} {'r_p99':>7} {'r_max':>8}  "
          f"{'w_p50':>6} {'w_p99':>7} {'w_max':>8}  {'>5s':>4} {'>10s':>5} {'op/s':>6}")
    for w in args.workers:
        shutil.rmtree(base, ignore_errors=True)
        base.mkdir(parents=True, exist_ok=True)
        _seed(db)
        r = run(w, args.secs, db)
        all_rows.append(r)
        print(f"  {r['workers']:>2}  {r['n_reads']:>6} {r['n_writes']:>6} "
              f"{r['n_errors']:>4}  {r['read_p50']:>6} {r['read_p99']:>7} "
              f"{r['read_max']:>8}  {r['write_p50']:>6} {r['write_p99']:>7} "
              f"{r['write_max']:>8}  {r['ops_over_5s']:>4} {r['ops_over_10s']:>5} "
              f"{r['throughput_ops_s']:>6}", flush=True)
        if r["error_samples"]:
            print(f"      errors: {r['error_samples']}", flush=True)
    if args.json_out:
        import json
        Path(args.json_out).write_text(
            json.dumps({"busy_timeout": bt, "secs": args.secs, "rows": all_rows},
                       indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
