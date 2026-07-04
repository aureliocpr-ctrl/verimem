"""Micro-bench latency del PPR fusion a REGIME (default-ON prereq #3b, 2026-06-14).

A differenza di bench_ppr_fusion.py (resetta _recall_es a ogni giro -> ricostruisce
il grafo) e dell'harness LongMemEval (FTS rebuild per-query, i 935ms ne sono
gonfiati), qui: store N fatti UNA volta, scalda i due path, poi misura il delta-ms
OFF vs ON con FTS trigger-synced gia' popolato e grafo cachato. E' il costo
STEADY-STATE che il default-ON pagherebbe in produzione.

ENGRAM_PPR_FUSION_BUDGET_S=0 -> nessun cap (misura il PPR pieno, non il budget).
Uso: python scripts/bench_fusion_latency.py [N] [Q_ITERS]
"""
from __future__ import annotations

import os
import statistics
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engram.entity_kg import Entity, EntityStore  # noqa: E402
from engram.entity_populate import entity_kg_path_for  # noqa: E402
from engram.semantic import Fact, SemanticMemory  # noqa: E402


def _p95(xs: list[float]) -> float:
    return sorted(xs)[min(len(xs) - 1, int(0.95 * len(xs)))]


def run(n: int = 300, q_iters: int = 40) -> None:
    tmp = Path(tempfile.mkdtemp(prefix="engram-lat-"))
    os.environ["ENGRAM_DATA_DIR"] = str(tmp)
    os.environ["ENGRAM_PPR_FUSION_BUDGET_S"] = "0"  # no cap: misura il PPR reale
    os.environ.pop("ENGRAM_PPR_FUSION_FLOOR", None)
    sm = SemanticMemory(db_path=tmp / "semantic" / "semantic.db")
    es = EntityStore(db_path=entity_kg_path_for(sm.db_path))

    for i in range(n):
        f = Fact(
            proposition=f"deploy service alpha_{i % 20} runbook step {i} "
                        f"status nominal config token deadbeef{i}",
            topic=f"t/{i % 10}",
        )
        sm.store(f, embed="sync")
        if i % 4 == 0:  # ~25% entity-linked, grafo realistico
            eid = es.store(Entity(canonical_name=f"alpha_{i % 20}", type="module"))
            es.add_edge(eid, eid, "self", weight=1.0)
            es.link_fact(f.id, eid)

    q = "deploy alpha_3 runbook deadbeef7"

    # warm-up entrambi i path (build grafo + FTS una volta, fuori dal timer)
    os.environ.pop("ENGRAM_PPR_FUSION", None)
    sm.recall(q, k=5)
    os.environ["ENGRAM_PPR_FUSION"] = "1"
    sm._recall_es = None
    sm.recall(q, k=5)

    os.environ.pop("ENGRAM_PPR_FUSION", None)
    off = []
    for _ in range(q_iters):
        t = time.perf_counter()
        sm.recall(q, k=5)
        off.append((time.perf_counter() - t) * 1000.0)

    os.environ["ENGRAM_PPR_FUSION"] = "1"
    on = []
    for _ in range(q_iters):
        t = time.perf_counter()
        sm.recall(q, k=5)
        on.append((time.perf_counter() - t) * 1000.0)

    print(f"n={n} fatti, q_iters={q_iters}, FTS persistente + grafo caldo")
    print(f"  OFF (cosine+rerank): mean={statistics.mean(off):6.1f}ms  p95={_p95(off):6.1f}ms")
    print(f"  ON  (3-signal)     : mean={statistics.mean(on):6.1f}ms  p95={_p95(on):6.1f}ms")
    print(f"  DELTA fusione      : mean={statistics.mean(on) - statistics.mean(off):+6.1f}ms  "
          f"p95={_p95(on) - _p95(off):+6.1f}ms")


if __name__ == "__main__":
    _n = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    _q = int(sys.argv[2]) if len(sys.argv) > 2 else 40
    run(_n, _q)
