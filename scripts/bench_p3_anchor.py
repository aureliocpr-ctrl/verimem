"""P3 anchor_recall latency bench — compare anchor_recall vs ppr()
vs facts_search keyword.

Setup sintetico (seed=70):
  - 5 anchor entity con half_life_days variabile (1, 3, 7, 14, 30)
  - 50 entity non-anchor (concept/person/org)
  - 100 edge random anchor↔entity + entity↔entity
  - 200 fact_id linked random

Misure per ogni mode (50 runs):
  - anchor_recall (decay + ppr_weighted, replicato in-script)
  - ppr() diretto su anchor_ids (no decay, personalization uniforme)
  - facts_search noop (baseline lower bound, no LLM)

Riproducibile. Zero LLM call. NO API cost.
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


def setup_corpus(db_path: Path) -> dict[str, Any]:
    from engram.entity_kg import Entity, EntityStore

    random.seed(70)
    store = EntityStore(db_path=db_path)
    now = time.time()

    # 5 anchor con half_life variabili + age diversi
    anchor_specs = [
        ("AnchorRecent", 1.0, 0.0),       # appena creato
        ("AnchorFreshish", 3.0, 1.0),     # 1d
        ("AnchorMidlife", 7.0, 5.0),      # 5d, ~0.61 decay
        ("AnchorOld", 14.0, 20.0),        # 20d, ~0.37 decay
        ("AnchorDecayed", 30.0, 90.0),    # 90d, ~0.13 decay
    ]
    anchor_ids: list[str] = []
    for name, hl, age_days in anchor_specs:
        eid = store.store(Entity(canonical_name=name, type="anchor"))
        store.set_attr(eid, "half_life_days", hl)
        store.set_attr(eid, "created_anchor_at",
                       now - age_days * 86400.0)
        anchor_ids.append(eid)

    # 50 entity non-anchor
    other_ids: list[str] = []
    for i in range(50):
        eid = store.store(Entity(
            canonical_name=f"Concept{i:03d}",
            type=random.choice(["concept", "person", "org"]),
        ))
        other_ids.append(eid)

    # 100 edge random (anchor->other + other->other)
    all_ids = anchor_ids + other_ids
    for _ in range(100):
        src, dst = random.sample(all_ids, 2)
        store.add_edge(src, dst, predicate="related_to",
                       weight=random.uniform(0.5, 1.5))

    # 200 fact link
    for i in range(200):
        store.link_fact(f"f_{i:04d}", random.choice(all_ids))

    return {
        "store": store,
        "anchor_ids": anchor_ids,
        "other_ids": other_ids,
    }


def bench_anchor_recall(env: dict[str, Any], runs: int = 50) -> dict[str, Any]:
    """Replica logic di mcp_server handler hippo_anchor_recall."""
    store = env["store"]
    threshold = 0.01

    latencies = []
    for _ in range(runs):
        t0 = _now()
        # 1) list_anchors
        anchors_raw = store.list_anchors()
        # 2) decay per ogni anchor
        now = time.time()
        anchors = []
        for a_row in anchors_raw:
            attrs = a_row["attrs"]
            hl = float(attrs.get("half_life_days", 7.0))
            cat = float(attrs.get("created_anchor_at", now))
            age_days = max(0.0, (now - cat) / 86400.0)
            w = 2.0 ** (-age_days / hl) if hl > 0 else 1.0
            if w >= threshold:
                anchors.append({"eid": a_row["entity_id"], "weight": w})
        # 3) personalization + ppr_weighted
        if anchors:
            pers = {a["eid"]: a["weight"] for a in anchors}
            store.ppr_weighted(pers, damping=0.5, k=20)
        latencies.append(_now() - t0)
    return {
        "runs": runs,
        "p50_ms": _ms(_percentile(latencies, 0.5)),
        "p95_ms": _ms(_percentile(latencies, 0.95)),
        "p99_ms": _ms(_percentile(latencies, 0.99)),
        "mean_ms": _ms(statistics.mean(latencies)),
        "max_ms": _ms(max(latencies)),
    }


def bench_ppr_direct(env: dict[str, Any], runs: int = 50) -> dict[str, Any]:
    store = env["store"]
    anchor_ids = env["anchor_ids"]
    latencies = []
    for _ in range(runs):
        t0 = _now()
        store.ppr(query_entities=anchor_ids, damping=0.5, k=20)
        latencies.append(_now() - t0)
    return {
        "runs": runs,
        "p50_ms": _ms(_percentile(latencies, 0.5)),
        "p95_ms": _ms(_percentile(latencies, 0.95)),
        "p99_ms": _ms(_percentile(latencies, 0.99)),
        "mean_ms": _ms(statistics.mean(latencies)),
        "max_ms": _ms(max(latencies)),
    }


def bench_facts_search_baseline(env: dict[str, Any], runs: int = 50) -> dict[str, Any]:
    """Baseline lower-bound: 1 SELECT su entity_facts (no PPR)."""
    store = env["store"]
    anchor_ids = env["anchor_ids"]
    latencies = []
    for _ in range(runs):
        t0 = _now()
        for eid in anchor_ids:
            store.facts_for_entity(eid)
        latencies.append(_now() - t0)
    return {
        "runs": runs,
        "p50_ms": _ms(_percentile(latencies, 0.5)),
        "p95_ms": _ms(_percentile(latencies, 0.95)),
        "p99_ms": _ms(_percentile(latencies, 0.99)),
        "mean_ms": _ms(statistics.mean(latencies)),
        "max_ms": _ms(max(latencies)),
    }


def main() -> int:
    out_dir = Path(__file__).resolve().parent.parent / "docs" / "bench"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("[setup] corpus sintetico 5 anchor + 50 entity + 100 edge...")
    with tempfile.TemporaryDirectory() as td:
        env = setup_corpus(Path(td) / "p3.db")

        print("[A] anchor_recall full (decay + ppr_weighted) x50 ...")
        anchor = bench_anchor_recall(env)
        print("[B] ppr() diretto (no decay, uniform pers) x50 ...")
        ppr = bench_ppr_direct(env)
        print("[C] facts_for_entity baseline x50 ...")
        facts = bench_facts_search_baseline(env)

    report = {
        "bench_name": "cycle-70-p3-anchor-latency",
        "timestamp_unix": time.time(),
        "setup": {
            "n_anchors": 5,
            "n_other_entities": 50,
            "n_edges": 100,
            "n_fact_links": 200,
            "anchor_age_days": [0, 1, 5, 20, 90],
            "anchor_half_life_days": [1, 3, 7, 14, 30],
        },
        "anchor_recall": anchor,
        "ppr_direct": ppr,
        "facts_for_entity_baseline": facts,
    }
    out_path = out_dir / "cycle-70-p3-anchor-latency.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nReport: {out_path}\n")

    print("## Summary\n")
    print("| Mode | p50 ms | p95 ms | p99 ms | mean ms |")
    print("|---|---|---|---|---|")
    for label, r in (
        ("anchor_recall (decay+ppr_weighted)", anchor),
        ("ppr() (uniform pers, no decay)", ppr),
        ("facts_for_entity (5 SELECT)", facts),
    ):
        print(f"| {label:42s} | "
              f"{r['p50_ms']:7.3f} | {r['p95_ms']:7.3f} | "
              f"{r['p99_ms']:7.3f} | {r['mean_ms']:7.3f} |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
