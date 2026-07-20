"""Concurrency stress — how does the store degrade with N concurrent clients?

The honest multi-user question: does N clients on ONE SQLite store stay usable,
or does latency explode? Each worker is a SEPARATE SemanticMemory with its OWN
connection (SQLite file-locks across connections identically whether thread or
process, so N threads = N clients for the lock). Fresh temp DB, isolated from
the real store. Reads (recall) and writes (add, which encodes) are timed
separately; we report p50/p95/p99 + errors so the degradation curve is visible.

Usage
  python -m benchmark.concurrency_stress --workers 1 5 --secs 12
"""
from __future__ import annotations

import argparse
import statistics
import shutil
import tempfile
import threading
import time
from pathlib import Path


def _pctl(xs: list[float], p: float) -> float:
    if not xs:
        return 0.0
    xs = sorted(xs)
    i = min(len(xs) - 1, int(round(p / 100.0 * (len(xs) - 1))))
    return round(xs[i] * 1000, 1)  # ms


def run(n_workers: int, secs: float, db_path: Path, shared_writer: bool = False) -> dict:
    from verimem.client import Memory
    # seed a little so recall has something to find
    seed = Memory(db_path)
    for i in range(30):
        seed.add(f"Seed fact number {i}: the widget subsystem handles case {i}.",
                 topic=f"seed/{i % 5}")
    # single-writer experiment: one shared Memory funnels ALL writes (as a
    # single-writer server would), while reads stay per-client via WAL.
    writer = Memory(db_path) if shared_writer else None
    wlock = threading.Lock()
    stop = time.time() + secs
    read_lat: list[float] = []
    write_lat: list[float] = []
    errors: list[str] = []
    locks = {"r": threading.Lock(), "w": threading.Lock(), "e": threading.Lock()}

    def worker(wid: int) -> None:
        mem = Memory(db_path)                      # each client = own connection
        it = 0
        while time.time() < stop:
            it += 1
            try:
                t = time.time()
                mem.search("widget subsystem case", k=5)
                with locks["r"]:
                    read_lat.append(time.time() - t)
            except Exception as exc:  # noqa: BLE001
                with locks["e"]:
                    errors.append(f"read:{type(exc).__name__}:{str(exc)[:60]}")
            if it % 4 == 0:                          # ~25% writes
                try:
                    t = time.time()
                    if writer is not None:
                        with wlock:
                            writer.add(f"Worker {wid} iter {it}: widget case at "
                                       f"{time.time():.3f}.", topic=f"w/{wid}")
                    else:
                        mem.add(f"Worker {wid} iter {it}: widget case at "
                                f"{time.time():.3f}.", topic=f"w/{wid}")
                    with locks["w"]:
                        write_lat.append(time.time() - t)
                except Exception as exc:  # noqa: BLE001
                    with locks["e"]:
                        errors.append(f"write:{type(exc).__name__}:{str(exc)[:60]}")

    threads = [threading.Thread(target=worker, args=(w,)) for w in range(n_workers)]
    t0 = time.time()
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    wall = time.time() - t0
    return {
        "workers": n_workers,
        "wall_s": round(wall, 1),
        "reads": len(read_lat), "writes": len(write_lat), "errors": len(errors),
        "read_p50": _pctl(read_lat, 50), "read_p95": _pctl(read_lat, 95),
        "read_p99": _pctl(read_lat, 99), "read_max": _pctl(read_lat, 100),
        "write_p50": _pctl(write_lat, 50), "write_p95": _pctl(write_lat, 95),
        "write_max": _pctl(write_lat, 100),
        "read_throughput_s": round(len(read_lat) / max(wall, 1e-9), 1),
        "error_samples": errors[:5],
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, nargs="+", default=[1, 5])
    ap.add_argument("--secs", type=float, default=12.0)
    ap.add_argument("--shared-writer", action="store_true")
    args = ap.parse_args()
    print(f"=== CONCURRENCY STRESS (one SQLite store, N clients, {args.secs}s each) ===")
    print(f"{'N':>3} {'reads':>6} {'r_p50':>7} {'r_p95':>7} {'r_p99':>7} {'r_max':>8} "
          f"{'writes':>6} {'w_p50':>7} {'w_p95':>7} {'w_max':>9} {'r_tput/s':>9} {'err':>4}")
    for n in args.workers:
        d = tempfile.mkdtemp()
        try:
            r = run(n, args.secs, Path(d) / "stress.db", shared_writer=args.shared_writer)
        finally:
            shutil.rmtree(d, ignore_errors=True)  # WinError32-safe: leak if held
        print(f"{r['workers']:>3} {r['reads']:>6} {r['read_p50']:>7} {r['read_p95']:>7} "
              f"{r['read_p99']:>7} {r['read_max']:>8} {r['writes']:>6} {r['write_p50']:>7} "
              f"{r['write_p95']:>7} {r['write_max']:>9} {r['read_throughput_s']:>9} "
              f"{r['errors']:>4}", flush=True)
        if r["error_samples"]:
            print(f"    errors: {r['error_samples']}", flush=True)


if __name__ == "__main__":
    main()
