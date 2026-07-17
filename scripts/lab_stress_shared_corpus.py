"""Lab 2026-05-17 — stress test shared corpus, multi-process write contention.

Aurelio direttiva: "voglio empiricamente e realmente funziona, lab reale".
Aurelio osservazione: "memoria non viene aggiornata live".

Scenario: simuliamo 2 sessioni Claude che scrivono fact concorrenti sul
semantic.db reale (~/.engram/semantic/semantic.db). Misuriamo:
- write throughput per process
- read latency parallela
- WAL busy_timeout impatto
- post-write read freshness (vede subito? quanto lag?)

NO MCP layer overhead — test diretto SemanticMemory.
Empirico, no marketing.
"""
from __future__ import annotations

import os
import sys
import time
from multiprocessing import Process, Queue
from pathlib import Path

# Ensure we can import verimem from repo root
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from verimem.semantic import Fact, SemanticMemory


def writer_worker(worker_id: int, db_path: str, n_writes: int, q: Queue) -> None:
    """Write n_writes facts under topic project/lab/stress-{worker_id}."""
    sm = SemanticMemory(db_path=Path(db_path))
    latencies_ms: list[float] = []
    for i in range(n_writes):
        f = Fact(
            id=f"lab-{worker_id}-{i}-{int(time.time()*1000)}",
            proposition=f"Lab stress test worker {worker_id} write {i} ts={time.time():.3f}",
            topic=f"project/lab/stress-w{worker_id}",
            confidence=0.5,
        )
        t0 = time.monotonic_ns()
        sm.store(f)
        dt_ms = (time.monotonic_ns() - t0) / 1e6
        latencies_ms.append(dt_ms)
    q.put(("write", worker_id, latencies_ms))


def reader_worker(worker_id: int, db_path: str, n_reads: int, q: Queue) -> None:
    """Concurrent read while writers are active."""
    sm = SemanticMemory(db_path=Path(db_path))
    latencies_ms: list[float] = []
    for i in range(n_reads):
        t0 = time.monotonic_ns()
        hits = sm.recall(query=f"lab stress test {i % 3}", k=10)
        dt_ms = (time.monotonic_ns() - t0) / 1e6
        latencies_ms.append(dt_ms)
    q.put(("read", worker_id, latencies_ms, len(hits) if hits else 0))


def pct(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    k = (len(s) - 1) * p
    f = int(k)
    c = min(f + 1, len(s) - 1)
    if f == c:
        return s[f]
    return s[f] * (c - k) + s[c] * (k - f)


def main() -> None:
    db_path = os.environ.get(
        "ENGRAM_LAB_DB",
        str(Path.home() / ".engram" / "semantic" / "semantic.db"),
    )
    n_writers = int(os.environ.get("LAB_N_WRITERS", "2"))
    n_writes_each = int(os.environ.get("LAB_N_WRITES", "50"))
    n_readers = int(os.environ.get("LAB_N_READERS", "2"))
    n_reads_each = int(os.environ.get("LAB_N_READS", "50"))

    print(f"[lab] db_path = {db_path}")
    print(f"[lab] writers={n_writers} writes_each={n_writes_each}")
    print(f"[lab] readers={n_readers} reads_each={n_reads_each}")
    print(f"[lab] total writes = {n_writers * n_writes_each}")

    q: Queue = Queue()
    procs: list[Process] = []
    t_start = time.monotonic()
    for wid in range(n_writers):
        p = Process(target=writer_worker, args=(wid, db_path, n_writes_each, q))
        p.start()
        procs.append(p)
    for rid in range(n_readers):
        p = Process(target=reader_worker, args=(rid, db_path, n_reads_each, q))
        p.start()
        procs.append(p)

    results = []
    for _ in range(n_writers + n_readers):
        results.append(q.get(timeout=120))

    for p in procs:
        p.join(timeout=30)

    t_total = time.monotonic() - t_start

    write_lat: list[float] = []
    read_lat: list[float] = []
    for r in results:
        kind = r[0]
        lat = r[2]
        if kind == "write":
            write_lat.extend(lat)
        else:
            read_lat.extend(lat)

    print()
    print(f"[lab] wallclock total: {t_total:.2f}s")
    print(f"[lab] write ops: {len(write_lat)}")
    print(f"  write p50: {pct(write_lat, 0.50):.1f}ms")
    print(f"  write p95: {pct(write_lat, 0.95):.1f}ms")
    print(f"  write p99: {pct(write_lat, 0.99):.1f}ms")
    print(f"  write max: {max(write_lat) if write_lat else 0:.1f}ms")
    print(f"  write throughput: {len(write_lat) / t_total:.1f} ops/s")
    print(f"[lab] read ops: {len(read_lat)}")
    print(f"  read p50: {pct(read_lat, 0.50):.1f}ms")
    print(f"  read p95: {pct(read_lat, 0.95):.1f}ms")
    print(f"  read p99: {pct(read_lat, 0.99):.1f}ms")
    print(f"  read max: {max(read_lat) if read_lat else 0:.1f}ms")

    # Freshness check: post-write, can we recall what we just wrote?
    print()
    print("[lab] FRESHNESS CHECK (live recall post-write):")
    sm = SemanticMemory(db_path=Path(db_path))
    fresh_lat: list[float] = []
    fresh_hits = 0
    for i in range(20):
        t0 = time.monotonic_ns()
        hits = sm.recall(query=f"lab stress test {i}", topic=None, k=10)
        dt_ms = (time.monotonic_ns() - t0) / 1e6
        fresh_lat.append(dt_ms)
        hit_topics = {h[0].topic for h in hits}
        if any("project/lab/stress" in t for t in hit_topics):
            fresh_hits += 1
    print(f"  fresh recall p50: {pct(fresh_lat, 0.50):.1f}ms")
    print(f"  recalls that find lab/stress topic: {fresh_hits}/20")


if __name__ == "__main__":
    main()
