#!/usr/bin/env python
"""Bench HYBRID BM25 + dense + Reciprocal Rank Fusion sul corpus Engram reale.

Ipotesi (da ricerca SOTA 2026): il nostro corpus e' pieno di IDENTIFICATORI
esatti (commit SHA, 'LOOP 273', 'PR #39', 'clp doctor', acronimi) su cui il
dense embedding e' debole e BM25 e' forte. La fusione RRF dei due ranking
dovrebbe alzare il recall senza tuning di score.

Confronta su 25 query IT etichettate (stessa label-set del recall-bench):
  - BM25-only        (rank_bm25, tokenizz. alfanumerica -> identificatori)
  - dense-only       (paraphrase-multilingual-MiniLM-L12-v2, il provato R@10=0.80)
  - HYBRID RRF       (fusione dei due, k=60)
Metriche: Recall@1/5/10/50 + MRR@10. Su COPIA del corpus, zero scrittura live.

Run:  python scripts/bench_hybrid_rrf.py
"""
from __future__ import annotations

import os
import re
import shutil
import sqlite3
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bench_recall_quality import LABELED  # noqa: E402

DENSE = "intfloat/multilingual-e5-base"  # vincitore sweep (R@10=0.84, gira su GPU 8GB)
DPFX, QPFX = "passage: ", "query: "       # e5 richiede questi prefissi
_TOK = re.compile(r"[a-z0-9]+")


def tok(s: str) -> list[str]:
    return _TOK.findall(s.lower())


def _load() -> tuple[list[str], list[str]]:
    src = os.path.expanduser("~/.engram/semantic/semantic.db")
    dst = os.path.join(tempfile.mkdtemp(prefix="bench_hy_"), "s.db")
    shutil.copy2(src, dst)
    c = sqlite3.connect(f"file:{dst}?mode=ro", uri=True)
    rows = c.execute(
        "SELECT id, proposition FROM facts WHERE superseded_by IS NULL "
        "AND status NOT IN ('quarantined','orphaned') AND length(proposition) > 0"
    ).fetchall()
    return [r[0][:10] for r in rows], [r[1] for r in rows]


def _metrics(rank_fn) -> dict:
    r1 = r5 = r10 = r50 = 0
    mrr = 0.0
    for i, (_, expected) in enumerate(LABELED):
        ranked = rank_fn(i)  # lista di id-prefix ordinata best-first (>=50)
        rank = ranked.index(expected) + 1 if expected in ranked else 0
        if rank == 1: r1 += 1
        if 1 <= rank <= 5: r5 += 1
        if 1 <= rank <= 10: r10 += 1
        if 1 <= rank <= 50: r50 += 1
        if 1 <= rank <= 10: mrr += 1.0 / rank
    n = len(LABELED)
    return {"R@1": r1/n, "R@5": r5/n, "R@10": r10/n, "R@50": r50/n, "MRR": mrr/n}


def _rrf(orders: list[list[int]], k: int = 60, topn: int = 60) -> list[int]:
    """Reciprocal Rank Fusion: score = sum 1/(k+rank). orders = liste di indici."""
    scores: dict[int, float] = {}
    for order in orders:
        for rank, idx in enumerate(order[:200]):
            scores[idx] = scores.get(idx, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores, key=lambda d: -scores[d])[:topn]


def main() -> int:
    ids, props = _load()
    queries = [q for q, _ in LABELED]
    print(f"=== HYBRID BM25+dense+RRF (corpus={len(ids)}, 25 query IT) ===", flush=True)

    from rank_bm25 import BM25Okapi
    bm25 = BM25Okapi([tok(p) for p in props])
    bm25_orders = [list(np.argsort(-bm25.get_scores(tok(q)))[:200]) for q in queries]

    from sentence_transformers import SentenceTransformer
    m = SentenceTransformer(DENSE, trust_remote_code=True)
    cemb = m.encode([DPFX + p for p in props], normalize_embeddings=True, convert_to_numpy=True,
                   show_progress_bar=False, batch_size=64).astype(np.float32)
    qemb = m.encode([QPFX + q for q in queries], normalize_embeddings=True, convert_to_numpy=True,
                   show_progress_bar=False, batch_size=64).astype(np.float32)
    dense_orders = [list(np.argsort(-(qemb[i] @ cemb.T))[:200]) for i in range(len(queries))]

    def bm25_rank(i):
        return [ids[j] for j in bm25_orders[i][:60]]

    def dense_rank(i):
        return [ids[j] for j in dense_orders[i][:60]]

    def hybrid_rank(i):
        return [ids[j] for j in _rrf([dense_orders[i], bm25_orders[i]])]

    b = _metrics(bm25_rank)
    d = _metrics(dense_rank)
    h = _metrics(hybrid_rank)
    print(f"BM25-only  : R@1={b['R@1']:.3f} R@5={b['R@5']:.3f} R@10={b['R@10']:.3f} R@50={b['R@50']:.3f} MRR={b['MRR']:.3f}", flush=True)
    print(f"dense-only : R@1={d['R@1']:.3f} R@5={d['R@5']:.3f} R@10={d['R@10']:.3f} R@50={d['R@50']:.3f} MRR={d['MRR']:.3f}", flush=True)
    print(f"HYBRID RRF : R@1={h['R@1']:.3f} R@5={h['R@5']:.3f} R@10={h['R@10']:.3f} R@50={h['R@50']:.3f} MRR={h['MRR']:.3f}", flush=True)
    dd = h["R@10"] - d["R@10"]
    print(f"--- hybrid vs dense: dR@10 {'+' if dd>=0 else ''}{dd:.3f} | dMRR {h['MRR']-d['MRR']:+.3f} ---", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
