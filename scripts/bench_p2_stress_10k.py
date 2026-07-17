"""P2 entity-centric KG — stress test 10k entity + 50k edges.

Misura empirica scaling oltre i 1000 nodi del bench iniziale:
  - Popolazione 10000 entity (warm path, single-thread)
  - 50000 edge random (avg degree 10)
  - PPR su seed di 5 entity, varia damping ∈ {0.3, 0.5, 0.85}
  - get_by_name p99 + neighbors p99

Zero LLM call. Riproducibile (seed=10000). NO API cost.
"""
from __future__ import annotations

import json
import random
import statistics
import sys
import tempfile
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


def bench_10k(db_path: Path) -> dict[str, Any]:
    from verimem.entity_kg import Entity, EntityStore

    random.seed(10000)
    store = EntityStore(db_path=db_path)

    # ---- Popolazione 10k entity ----
    t0 = _now()
    eids: list[str] = []
    for i in range(10000):
        eid = store.store(Entity(
            canonical_name=f"Entity{i:06d}",
            type=random.choice(["person", "paper", "org", "concept"]),
        ))
        eids.append(eid)
    populate_s = _now() - t0
    print(f"  populated 10k entities in {populate_s:.2f}s "
          f"({10000 / populate_s:.0f} ent/s)")

    # ---- 50k edges ----
    t0 = _now()
    for _ in range(50000):
        src, dst = random.sample(eids, 2)
        store.add_edge(
            src, dst, predicate=random.choice([
                "links_to", "cites", "co-authored",
                "affiliated_with", "located_in",
            ]),
            weight=random.uniform(0.3, 2.0),
        )
    edges_s = _now() - t0
    print(f"  added 50k edges in {edges_s:.2f}s "
          f"({50000 / edges_s:.0f} edge/s)")

    # ---- Workload read ----
    # get_by_name: 200 random query
    lat_get = []
    for _ in range(200):
        target_i = random.randrange(10000)
        t0 = _now()
        ent = store.get_by_name(f"Entity{target_i:06d}")
        lat_get.append(_now() - t0)
        assert ent is not None

    # neighbors hops=1: 100 query
    lat_nbr1 = []
    for _ in range(100):
        target = random.choice(eids)
        t0 = _now()
        store.neighbors(target, k=20, hops=1)
        lat_nbr1.append(_now() - t0)

    # neighbors hops=2: 50 query (heavier)
    lat_nbr2 = []
    for _ in range(50):
        target = random.choice(eids)
        t0 = _now()
        store.neighbors(target, k=20, hops=2)
        lat_nbr2.append(_now() - t0)

    # PPR vari damping
    ppr_results = {}
    seed_set = random.sample(eids, 5)
    for damping in (0.3, 0.5, 0.85):
        lat_ppr = []
        for _ in range(5):
            t0 = _now()
            store.ppr(query_entities=seed_set, damping=damping, k=20)
            lat_ppr.append(_now() - t0)
        ppr_results[f"damping_{damping}"] = {
            "n": len(lat_ppr),
            "min_ms": _ms(min(lat_ppr)),
            "mean_ms": _ms(statistics.mean(lat_ppr)),
            "max_ms": _ms(max(lat_ppr)),
        }

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
        "n_entities": 10000,
        "n_edges_attempted": 50000,
        "populate_s": round(populate_s, 3),
        "populate_throughput_ent_per_s": round(
            10000 / populate_s, 1,
        ),
        "edges_s": round(edges_s, 3),
        "edges_throughput_per_s": round(50000 / edges_s, 1),
        "read_stats": [
            stats(lat_get, "get_by_name (200 queries)"),
            stats(lat_nbr1, "neighbors(hops=1) (100)"),
            stats(lat_nbr2, "neighbors(hops=2) (50)"),
        ],
        "ppr_by_damping": ppr_results,
        "db_size_bytes": db_path.stat().st_size,
    }


def main() -> int:
    out_dir = Path(__file__).resolve().parent.parent / "docs" / "bench"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("[stress-10k] popolazione + workload su grafo 10k/50k...")
    with tempfile.TemporaryDirectory() as td:
        result = bench_10k(Path(td) / "stress10k.db")

    out_path = out_dir / "cycle-70-p2-stress-10k.json"
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"\nReport: {out_path}")

    print("\n## Stress-10k Summary\n")
    print(f"- populate: 10000 entities in {result['populate_s']:.2f}s "
          f"({result['populate_throughput_ent_per_s']:.0f} ent/s)")
    print(f"- edges: 50000 in {result['edges_s']:.2f}s "
          f"({result['edges_throughput_per_s']:.0f} edge/s)")
    print(f"- DB size: {result['db_size_bytes'] / 1024 / 1024:.2f} MB\n")
    for s in result["read_stats"]:
        if s["n"] == 0:
            continue
        print(f"- {s['label']:32s} "
              f"p50={s['p50_ms']:7.2f} ms  "
              f"p95={s['p95_ms']:7.2f} ms  "
              f"p99={s['p99_ms']:7.2f} ms")
    print()
    for d, r in result["ppr_by_damping"].items():
        print(f"- PPR {d:14s} "
              f"min={r['min_ms']:7.2f} ms  "
              f"mean={r['mean_ms']:7.2f} ms  "
              f"max={r['max_ms']:7.2f} ms")
    return 0


if __name__ == "__main__":
    sys.exit(main())
