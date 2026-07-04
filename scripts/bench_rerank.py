#!/usr/bin/env python
"""Bench RERANKING cross-encoder sul corpus Engram reale.

Pattern SOTA: dense retrieve top-N -> cross-encoder rerank -> top-k. Il reranker
NON aumenta il tetto di recall (puo' solo riordinare i candidati gia' recuperati)
ma alza precisione-in-cima (R@1, MRR): porta il fatto giusto piu' su nel top-N.

Confronto su 25 query IT etichettate:
  - dense-only           (paraphrase-multilingual top-50, ordine cosine)
  - dense + rerank       (stessi top-50, riordinati da bge-reranker-v2-m3)
Metriche: R@1/5/10 + MRR@10 (R@50 invariato = tetto del retriever). COPIA, no live.

Run:  python scripts/bench_rerank.py   (scarica il reranker la 1a volta)
"""
from __future__ import annotations

import os
import shutil
import sqlite3
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bench_recall_quality import LABELED  # noqa: E402

DENSE = "intfloat/multilingual-e5-base"   # vincitore sweep (R@10=0.84)
DPFX, QPFX = "passage: ", "query: "        # prefissi e5
RERANKER = "BAAI/bge-reranker-v2-m3"
TOPN = 50  # shortlist da riordinare


def _load() -> tuple[list[str], list[str]]:
    src = os.path.expanduser("~/.engram/semantic/semantic.db")
    dst = os.path.join(tempfile.mkdtemp(prefix="bench_rr_"), "s.db")
    shutil.copy2(src, dst)
    c = sqlite3.connect(f"file:{dst}?mode=ro", uri=True)
    rows = c.execute(
        "SELECT id, proposition FROM facts WHERE superseded_by IS NULL "
        "AND status NOT IN ('quarantined','orphaned') AND length(proposition) > 0"
    ).fetchall()
    return [r[0][:10] for r in rows], [r[1] for r in rows]


def _metrics(ranked_lists: list[list[str]]) -> dict:
    r1 = r5 = r10 = 0
    mrr = 0.0
    for (_, expected), ranked in zip(LABELED, ranked_lists, strict=False):
        rank = ranked.index(expected) + 1 if expected in ranked else 0
        if rank == 1: r1 += 1
        if 1 <= rank <= 5: r5 += 1
        if 1 <= rank <= 10: r10 += 1
        if 1 <= rank <= 10: mrr += 1.0 / rank
    n = len(LABELED)
    return {"R@1": r1/n, "R@5": r5/n, "R@10": r10/n, "MRR": mrr/n}


def main() -> int:
    ids, props = _load()
    queries = [q for q, _ in LABELED]
    print(f"=== RERANK (dense top-{TOPN} -> {RERANKER}) corpus={len(ids)}, 25 query IT ===", flush=True)

    from sentence_transformers import SentenceTransformer
    m = SentenceTransformer(DENSE, trust_remote_code=True)
    cemb = m.encode([DPFX + p for p in props], normalize_embeddings=True, convert_to_numpy=True,
                   show_progress_bar=False, batch_size=64).astype(np.float32)
    qemb = m.encode([QPFX + q for q in queries], normalize_embeddings=True, convert_to_numpy=True,
                   show_progress_bar=False, batch_size=64).astype(np.float32)
    # shortlist dense top-N (indici)
    shortlists = [list(np.argsort(-(qemb[i] @ cemb.T))[:TOPN]) for i in range(len(queries))]
    dense_ranked = [[ids[j] for j in sl] for sl in shortlists]

    from sentence_transformers import CrossEncoder
    ce = CrossEncoder(RERANKER, trust_remote_code=True, max_length=512, device="cpu")  # CPU: evita OOM GPU 8GB
    rerank_ranked = []
    for i, sl in enumerate(shortlists):
        pairs = [(queries[i], props[j]) for j in sl]
        scores = ce.predict(pairs, show_progress_bar=False)
        order = np.argsort(-np.asarray(scores))
        rerank_ranked.append([ids[sl[k]] for k in order])

    d = _metrics(dense_ranked)
    r = _metrics(rerank_ranked)
    print(f"dense-only      : R@1={d['R@1']:.3f} R@5={d['R@5']:.3f} R@10={d['R@10']:.3f} MRR={d['MRR']:.3f}", flush=True)
    print(f"dense + rerank  : R@1={r['R@1']:.3f} R@5={r['R@5']:.3f} R@10={r['R@10']:.3f} MRR={r['MRR']:.3f}", flush=True)
    print(f"--- rerank vs dense: dR@1 {r['R@1']-d['R@1']:+.3f} | dR@10 {r['R@10']-d['R@10']:+.3f} | dMRR {r['MRR']-d['MRR']:+.3f} ---", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
