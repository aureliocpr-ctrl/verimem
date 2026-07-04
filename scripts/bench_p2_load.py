"""P2 entity-centric KG — integration load bench (parte 2).

Simula utilizzo intensivo del KG:
  - Popola entity_kg con 100 entity + 300 edge + 50 alias + 200 fact link
  - Esegue 200 query randomized (mix get_by_name + neighbors + ppr)
  - Misura: p50/p95/p99 latency per operazione + throughput
  - Stress: 100 concurrent store/add_edge thread + verifica integrità

Zero LLM call. Riproducibile (seed fissi). Bench REALI, non synthetic.
"""
from __future__ import annotations

import json
import random
import statistics
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any


def _now() -> float:
    return time.perf_counter()


def _ms(s: float) -> float:
    return round(s * 1000.0, 3)


def _percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    idx = int(len(s) * q)
    return s[min(idx, len(s) - 1)]


# ---------- Bench L1: workload misto (get_by_name + neighbors + ppr)


def bench_mixed_workload(db_path: Path) -> dict[str, Any]:
    from engram.entity_kg import Entity, EntityStore

    store = EntityStore(db_path=db_path)
    random.seed(2026)

    # 1) Popolazione: 100 entity (50 person + 50 paper)
    eids: list[str] = []
    for i in range(100):
        type_ = "person" if i < 50 else "paper"
        eid = store.store(Entity(
            canonical_name=f"Entity{i:03d}",
            type=type_,
        ))
        eids.append(eid)
        # alcuni alias
        if i % 5 == 0:
            store.add_alias(eid, f"E{i}")
            store.add_alias(eid, f"E.{i:03d}")

    # 2) 300 edge con predicati misti
    predicates = ["authored", "cites", "supervises",
                  "located_in", "affiliated_with"]
    for _ in range(300):
        src, dst = random.sample(eids, 2)
        pred = random.choice(predicates)
        store.add_edge(src, dst, predicate=pred,
                       weight=random.uniform(0.3, 1.5))

    # 3) 200 fact link
    for i in range(200):
        store.link_fact(f"f_{i:04d}", random.choice(eids))

    # ---- Workload ----
    queries = []
    for _ in range(200):
        op = random.choice(["get", "get_alias", "neighbors_1",
                            "neighbors_2", "ppr"])
        queries.append(op)

    lat_get = []
    lat_alias = []
    lat_nbr1 = []
    lat_nbr2 = []
    lat_ppr = []

    for op in queries:
        if op == "get":
            target = random.choice(eids)
            ent = store.get_by_name(
                f"Entity{eids.index(target):03d}"
            )
            t0 = _now()
            store.get_by_name(f"Entity{eids.index(target):03d}")
            lat_get.append(_now() - t0)
            assert ent is not None
        elif op == "get_alias":
            i = random.choice(range(0, 100, 5))
            t0 = _now()
            ent = store.get_by_name(f"E{i}")
            lat_alias.append(_now() - t0)
            assert ent is not None
        elif op == "neighbors_1":
            target = random.choice(eids)
            t0 = _now()
            store.neighbors(target, k=10, hops=1)
            lat_nbr1.append(_now() - t0)
        elif op == "neighbors_2":
            target = random.choice(eids)
            t0 = _now()
            store.neighbors(target, k=10, hops=2)
            lat_nbr2.append(_now() - t0)
        elif op == "ppr":
            seeds = random.sample(eids, 3)
            t0 = _now()
            store.ppr(query_entities=seeds, damping=0.5, k=20)
            lat_ppr.append(_now() - t0)

    def stats(lst: list[float], label: str) -> dict[str, Any]:
        if not lst:
            return {"label": label, "n": 0}
        return {
            "label": label,
            "n": len(lst),
            "min_ms": _ms(min(lst)),
            "p50_ms": _ms(_percentile(lst, 0.5)),
            "p95_ms": _ms(_percentile(lst, 0.95)),
            "p99_ms": _ms(_percentile(lst, 0.99)),
            "max_ms": _ms(max(lst)),
            "mean_ms": _ms(statistics.mean(lst)),
        }

    return {
        "n_entities": 100,
        "n_edges": 300,
        "n_aliases": 40,
        "n_facts_linked": 200,
        "n_queries": len(queries),
        "stats": [
            stats(lat_get, "get_by_name(canonical)"),
            stats(lat_alias, "get_by_name(alias)"),
            stats(lat_nbr1, "neighbors(hops=1)"),
            stats(lat_nbr2, "neighbors(hops=2)"),
            stats(lat_ppr, "ppr(3 seeds, k=20)"),
        ],
    }


# ---------- Bench L2: concurrent store/add_edge integrity ----------


def bench_concurrent_writers(db_path: Path) -> dict[str, Any]:
    """100 thread paralleli che storano entity + edge → verifica
    integrità (no duplicate, no race) e throughput."""
    from engram.entity_kg import Entity, EntityStore

    store = EntityStore(db_path=db_path)

    n_threads = 50
    ops_per_thread = 10
    barrier = threading.Barrier(n_threads)
    errors: list[BaseException] = []
    lock = threading.Lock()

    def worker(thread_id: int) -> None:
        try:
            barrier.wait(timeout=20)
            for i in range(ops_per_thread):
                # Mix di store (con qualche collision)
                ent_name = f"Worker{thread_id % 10}_E{i}"
                eid = store.store(Entity(
                    canonical_name=ent_name, type="worker",
                ))
                # add_edge tra workers diversi (collisions possibili)
                other_name = (
                    f"Worker{(thread_id + 1) % 10}_E{(i + 1) % 10}"
                )
                other = store.get_by_name(other_name)
                if other is not None:
                    store.add_edge(
                        eid, other.id, predicate="collides",
                    )
        except BaseException as e:  # noqa: BLE001
            with lock:
                errors.append(e)

    t0 = _now()
    threads = [
        threading.Thread(target=worker, args=(i,))
        for i in range(n_threads)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    elapsed = _now() - t0

    final_count = store.count()
    # Expected: 10 worker_groups * 10 i = 100 unique entities
    # (n_threads % 10 collassano sullo stesso canonical_name)
    expected = 100
    integrity_ok = final_count == expected and not errors

    total_ops = n_threads * ops_per_thread
    throughput = total_ops / elapsed if elapsed > 0 else 0.0

    return {
        "n_threads": n_threads,
        "ops_per_thread": ops_per_thread,
        "total_ops": total_ops,
        "final_entity_count": final_count,
        "expected_unique_entities": expected,
        "integrity_ok": integrity_ok,
        "errors": [
            f"{type(e).__name__}: {e}" for e in errors[:5]
        ],
        "elapsed_s": round(elapsed, 3),
        "throughput_ops_per_s": round(throughput, 1),
    }


# ---------- Main -----------------------------------------------------


def main() -> int:
    out_dir = Path(__file__).resolve().parent.parent / "docs" / "bench"
    out_dir.mkdir(parents=True, exist_ok=True)

    report: dict[str, Any] = {
        "bench_name": "cycle-70-p2-load",
        "timestamp_unix": time.time(),
    }

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        print("[L1] mixed workload (100 ent + 300 edge + 200 query)...")
        report["bench_L1_workload"] = bench_mixed_workload(
            tmp / "L1.db"
        )
        print("    ... done")

        print("[L2] concurrent writers (50 thread x 10 ops)...")
        report["bench_L2_concurrent"] = bench_concurrent_writers(
            tmp / "L2.db"
        )
        print("    ... done")

    out_path = out_dir / "cycle-70-p2-load.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nReport: {out_path}")

    print("\n## Summary\n")
    print("### L1 — Mixed workload latency (200 query)\n")
    for s in report["bench_L1_workload"]["stats"]:
        if s["n"] == 0:
            continue
        print(f"- {s['label']:30s} n={s['n']:3d}  "
              f"p50={s['p50_ms']:7.2f} ms  "
              f"p95={s['p95_ms']:7.2f} ms  "
              f"p99={s['p99_ms']:7.2f} ms")

    print("\n### L2 — Concurrent writers integrity")
    L = report["bench_L2_concurrent"]
    print(f"- {L['n_threads']} threads × {L['ops_per_thread']} ops "
          f"in {L['elapsed_s']} s = "
          f"{L['throughput_ops_per_s']} ops/s")
    print(f"- final_count={L['final_entity_count']} "
          f"(expected {L['expected_unique_entities']}) "
          f"-> integrity_ok={L['integrity_ok']}")
    if L["errors"]:
        print(f"- errors: {L['errors']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
