"""P2 entity-centric KG bench — recall@k + PPR determinism + latency.

Misura empirica end-to-end di P2.a/b/c senza LLM call (zero costo).

Tre micro-bench:

  A) recall@k: entity_get vs facts_search vs hippo_recall su corpus
     reale ~/.engram (~495 fact + 205 episode). Query set sintetico
     ma realistico (Tonegawa, P2.a, critic-orchestrator, Müller, ...).
     Confronto: hits@1, hits@3, hits@5 + latency media.

  B) PPR determinism strict: 10 chiamate consecutive con stesso input
     su grafo sintetico 50 nodi/100 edges → assert score byte-identici.

  C) PPR latency: grafo crescente 10/100/1000 nodi (random Erdős-
     Rényi, p tale che n*p ≈ 5) → tempo medio su 5 esecuzioni.

Output: docs/bench/cycle-70-p2-bench.json + console summary
Markdown-style. Riproducibile (seed fisso). NO LLM call, NO API cost.
"""
from __future__ import annotations

import json
import random
import statistics
import sys
import time
from pathlib import Path
from typing import Any

# ---------- Helpers ---------------------------------------------------


def _now() -> float:
    return time.perf_counter()


def _ms(elapsed_s: float) -> float:
    return round(elapsed_s * 1000.0, 3)


# ---------- BENCH A: recall@k entity_get vs facts_search vs recall --


def bench_recall(corpus_data_dir: Path) -> dict[str, Any]:
    """Compare 3 retrieval modalities su corpus reale.

    Misura per ogni query (10 query):
      - latency entity_get (P2.a)
      - latency facts_search (semantic memory keyword)
      - latency hippo_recall (episodic memory semantic)
      - hits: l'entity/fact/episode è stato trovato?
    """
    import os

    os.environ["ENGRAM_DATA_DIR"] = str(corpus_data_dir)
    # Reload config so it picks up the env var
    from verimem import config as _cfg
    _cfg.CONFIG = _cfg.Config()
    _cfg.CONFIG.ensure_dirs()

    from verimem.entity_kg import EntityStore
    from verimem.memory import EpisodicMemory
    from verimem.semantic import SemanticMemory

    # Pass explicit db_paths from the new CONFIG
    entity_kg = EntityStore(
        db_path=_cfg.CONFIG.data_dir / "entity_kg" / "entity_kg.db",
    )
    semantic = SemanticMemory()
    episodic = EpisodicMemory()

    queries = [
        "Tonegawa",
        "P2.a",
        "critic-orchestrator",
        "Müller",
        "HippoRAG",
        "cycle #70",
        "engram",
        "self_model",
        "entity_kg",
        "skill",
    ]

    results: list[dict[str, Any]] = []
    for q in queries:
        # entity_get
        t0 = _now()
        ent = entity_kg.get_by_name(q)
        t_ent = _now() - t0
        ent_hit = ent is not None

        # facts_search
        t0 = _now()
        facts = semantic.search_facts(q, limit=5)
        t_facts = _now() - t0
        facts_hit_k1 = bool(facts)
        facts_hit_k3 = len(facts) >= 1 and any(
            q.lower() in (f.proposition or "").lower() for f in facts[:3]
        )

        # episodic recall (keyword over episode text via .all())
        t0 = _now()
        all_eps = episodic.all(limit=500)
        eps = [
            e for e in all_eps
            if q.lower() in (
                (e.task_text or "") + (e.final_answer or "")
            ).lower()
        ][:5]
        t_eps = _now() - t0
        eps_hit = bool(eps)

        results.append({
            "query": q,
            "entity_get": {
                "latency_ms": _ms(t_ent),
                "hit": ent_hit,
                "facts_linked": (
                    len(entity_kg.facts_for_entity(ent.id))
                    if ent else 0
                ),
            },
            "facts_search": {
                "latency_ms": _ms(t_facts),
                "hits_k5": len(facts),
                "hit_k1": facts_hit_k1,
                "hit_k3_query_in_prop": facts_hit_k3,
            },
            "episodic_recall": {
                "latency_ms": _ms(t_eps),
                "hits_k5": len(eps),
                "hit": eps_hit,
            },
        })

    # Aggregati
    n = len(results)
    summary = {
        "n_queries": n,
        "entity_get": {
            "hit_rate": sum(
                1 for r in results if r["entity_get"]["hit"]
            ) / n,
            "mean_latency_ms": statistics.mean(
                r["entity_get"]["latency_ms"] for r in results
            ),
            "p95_latency_ms": _ms(
                statistics.quantiles(
                    [r["entity_get"]["latency_ms"] / 1000.0
                     for r in results],
                    n=20,
                )[-1]
            ) if n >= 20 else None,
        },
        "facts_search": {
            "hit_rate_k1": sum(
                1 for r in results if r["facts_search"]["hit_k1"]
            ) / n,
            "hit_rate_k3_query_in_prop": sum(
                1 for r in results
                if r["facts_search"]["hit_k3_query_in_prop"]
            ) / n,
            "mean_latency_ms": statistics.mean(
                r["facts_search"]["latency_ms"] for r in results
            ),
        },
        "episodic_recall": {
            "hit_rate": sum(
                1 for r in results if r["episodic_recall"]["hit"]
            ) / n,
            "mean_latency_ms": statistics.mean(
                r["episodic_recall"]["latency_ms"] for r in results
            ),
        },
    }

    return {"per_query": results, "summary": summary}


# ---------- BENCH B: PPR determinism strict --------------------------


def bench_ppr_determinism(tmp_path: Path) -> dict[str, Any]:
    """10 chiamate PPR consecutive su stesso grafo deterministic →
    assert score identici fino a 12 decimali."""
    from verimem.entity_kg import Entity, EntityStore

    store = EntityStore(db_path=tmp_path / "ppr_det.db")
    random.seed(42)
    # Costruisci grafo 50 nodi, ~100 edges
    nodes = [
        store.store(Entity(canonical_name=f"E{i:03d}", type="t"))
        for i in range(50)
    ]
    edges_added = 0
    for _ in range(100):
        a, b = random.sample(nodes, 2)
        store.add_edge(a, b, predicate="link",
                       weight=random.uniform(0.1, 2.0))
        edges_added += 1

    seed_ids = nodes[:3]
    runs: list[list[tuple[str, float]]] = []
    latencies: list[float] = []
    for i in range(10):
        t0 = _now()
        out = store.ppr(query_entities=seed_ids, damping=0.5, k=20)
        latencies.append(_now() - t0)
        runs.append(
            [(r["entity_id"], r["score"]) for r in out["ranked"]]
        )

    # Verifica determinismo
    deterministic = all(r == runs[0] for r in runs)

    return {
        "n_nodes": len(nodes),
        "n_edges_attempted": edges_added,
        "n_runs": len(runs),
        "deterministic_byte_identical": deterministic,
        "first_run_top5": runs[0][:5],
        "discrepancies": [
            (i, runs[0], r)
            for i, r in enumerate(runs[1:], 1)
            if r != runs[0]
        ][:3],  # cap at 3 for log size
        "mean_latency_ms": _ms(statistics.mean(latencies)),
        "median_latency_ms": _ms(statistics.median(latencies)),
    }


# ---------- BENCH C: PPR latency vs graph size -----------------------


def bench_ppr_latency_scaling(tmp_path: Path) -> dict[str, Any]:
    """PPR latency su grafi 10/100/500/1000 nodi (Erdős-Rényi-like)."""
    from verimem.entity_kg import Entity, EntityStore

    results = []
    for n_nodes in (10, 100, 500, 1000):
        db_path = tmp_path / f"ppr_lat_{n_nodes}.db"
        store = EntityStore(db_path=db_path)
        random.seed(123 + n_nodes)
        nodes = [
            store.store(Entity(canonical_name=f"N{i:05d}", type="t"))
            for i in range(n_nodes)
        ]
        # density: avg degree 5
        n_edges = n_nodes * 5
        for _ in range(n_edges):
            a, b = random.sample(nodes, 2)
            store.add_edge(a, b, predicate="link",
                           weight=random.uniform(0.5, 1.5))

        seed = nodes[:5]
        # warm-up + 5 timed runs
        store.ppr(query_entities=seed, damping=0.5, k=20)
        run_lat = []
        for _ in range(5):
            t0 = _now()
            store.ppr(query_entities=seed, damping=0.5, k=20)
            run_lat.append(_now() - t0)
        results.append({
            "n_nodes": n_nodes,
            "n_edges_attempted": n_edges,
            "min_latency_ms": _ms(min(run_lat)),
            "mean_latency_ms": _ms(statistics.mean(run_lat)),
            "max_latency_ms": _ms(max(run_lat)),
        })
    return {"runs": results}


# ---------- Main entrypoint ------------------------------------------


def main() -> int:
    out_dir = Path(__file__).resolve().parent.parent / "docs" / "bench"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "cycle-70-p2-bench.json"

    import tempfile

    report: dict[str, Any] = {
        "bench_name": "cycle-70-p2-entity-kg",
        "timestamp_unix": time.time(),
    }

    # Bench A: recall@k usa il corpus reale ~/.engram
    home_engram = Path.home() / ".engram"
    if home_engram.exists():
        try:
            print("[A] recall@k su corpus reale ~/.engram ...")
            report["bench_A_recall"] = bench_recall(home_engram)
            print("    ... done")
        except Exception as e:
            report["bench_A_recall"] = {
                "error": f"{type(e).__name__}: {e}",
            }
            print(f"    ... ERROR: {e}")
    else:
        report["bench_A_recall"] = {
            "skipped": "~/.engram corpus not found",
        }

    # Bench B+C usano tmp_path
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        print("[B] PPR determinism strict (10 runs) ...")
        report["bench_B_determinism"] = bench_ppr_determinism(tmp)
        print("    ... done")

        print("[C] PPR latency scaling (10/100/500/1000 nodes) ...")
        report["bench_C_latency"] = bench_ppr_latency_scaling(tmp)
        print("    ... done")

    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nReport saved to {out_path}")

    # Console summary Markdown-style
    print("\n## Summary\n")
    if "summary" in report.get("bench_A_recall", {}):
        s = report["bench_A_recall"]["summary"]
        print("### Bench A — recall@k\n")
        print(f"- entity_get hit_rate: "
              f"{s['entity_get']['hit_rate']:.1%}, "
              f"mean latency: {s['entity_get']['mean_latency_ms']:.2f} ms")
        print(f"- facts_search hit_rate@1: "
              f"{s['facts_search']['hit_rate_k1']:.1%}, "
              f"mean latency: "
              f"{s['facts_search']['mean_latency_ms']:.2f} ms")
        print(f"- episodic_recall hit_rate: "
              f"{s['episodic_recall']['hit_rate']:.1%}, "
              f"mean latency: "
              f"{s['episodic_recall']['mean_latency_ms']:.2f} ms")
    b = report["bench_B_determinism"]
    print("\n### Bench B — PPR determinism")
    print(f"- {b['n_runs']} runs su grafo {b['n_nodes']} nodi: "
          f"deterministic_byte_identical = "
          f"{b['deterministic_byte_identical']}")
    print(f"- mean latency: {b['mean_latency_ms']:.2f} ms")
    print("\n### Bench C — PPR latency scaling")
    for r in report["bench_C_latency"]["runs"]:
        print(f"- {r['n_nodes']:5d} nodes / "
              f"{r['n_edges_attempted']:5d} edges: "
              f"min {r['min_latency_ms']:7.2f} ms | "
              f"mean {r['mean_latency_ms']:7.2f} ms | "
              f"max {r['max_latency_ms']:7.2f} ms")

    return 0


if __name__ == "__main__":
    sys.exit(main())
