#!/usr/bin/env python
"""Bench PUNTO-DI-SVOLTA: reranker SOPRA lo stack LIVE multilingue.

Diverso da ``bench_rerank.py`` (che usa e5-base 768d, NON il modello live): qui si
misura il lift del cross-encoder ``bge-reranker-v2-m3`` sul recall REALE di
produzione — ``SemanticMemory`` col modello multilingue ATTIVO (post-flip 2026-06-04).
È esattamente il path ``verimem.rerank.recall_reranked`` che si attiverebbe con
``HIPPO_RERANK=1``: 2 stadi (recall dense top-50 con gate+v9 -> bge-reranker -> top-10).

Su COPIA del corpus live, 25 query IT etichettate a mano. Hermetic (mai scrive live).
Run: python scripts/bench_rerank_live.py   (scarica il reranker la 1a volta)
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

os.environ["ENGRAM_RECALL_RERANK"] = "0"  # CE default-ON since 2026-06-10 — dense arm must stay bi-encoder
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bench_recall_quality import LABELED  # noqa: E402


def _metrics(ranked_lists: list[list[str]]) -> dict:
    r1 = r5 = r10 = 0
    mrr = 0.0
    for (_, expected), ranked in zip(LABELED, ranked_lists, strict=False):
        rank = ranked.index(expected) + 1 if expected in ranked else 0
        if rank == 1:
            r1 += 1
        if 1 <= rank <= 5:
            r5 += 1
        if 1 <= rank <= 10:
            r10 += 1
            mrr += 1.0 / rank
    n = len(LABELED)
    return {"R@1": r1 / n, "R@5": r5 / n, "R@10": r10 / n, "MRR": mrr / n}


def main() -> int:
    from verimem import embedding as emb
    from verimem.rerank import recall_reranked
    from verimem.semantic import SemanticMemory

    src = os.path.expanduser("~/.engram/semantic/semantic.db")
    dst = Path(tempfile.mkdtemp(prefix="bench_rr_live_")) / "s.db"
    shutil.copy2(src, dst)
    sm = SemanticMemory(db_path=dst)
    emb.encode("warmup")
    print(f"=== RERANK LIVE-STACK | model={emb.model_signature()} | corpus copy | 25 query IT ===", flush=True)

    dense_ranked, rr_ranked = [], []
    t0 = time.time()
    for q, _ in LABELED:
        hits = sm.recall(q, k=50)
        dense_ranked.append([f.id[:10] for f, *_ in hits][:10])
    t_dense = time.time() - t0

    t0 = time.time()
    for q, _ in LABELED:
        rr = recall_reranked(sm, q, k=10, pool=50)
        rr_ranked.append([f.id[:10] for f, *_ in rr])
    t_rr = time.time() - t0

    d = _metrics(dense_ranked)
    r = _metrics(rr_ranked)
    print(f"dense (multilingue) : R@1={d['R@1']:.3f} R@5={d['R@5']:.3f} R@10={d['R@10']:.3f} MRR={d['MRR']:.3f}  ({t_dense:.1f}s, {t_dense/len(LABELED)*1000:.0f}ms/q)", flush=True)
    print(f"dense + bge-rerank  : R@1={r['R@1']:.3f} R@5={r['R@5']:.3f} R@10={r['R@10']:.3f} MRR={r['MRR']:.3f}  ({t_rr:.1f}s, {t_rr/len(LABELED)*1000:.0f}ms/q)", flush=True)
    print(f"--- LIFT rerank: dMRR {r['MRR']-d['MRR']:+.3f} | dR@1 {r['R@1']-d['R@1']:+.3f} | dR@10 {r['R@10']-d['R@10']:+.3f} ---", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
