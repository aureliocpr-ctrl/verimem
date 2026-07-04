#!/usr/bin/env python
"""Bench e5-base DENSE-ONLY (no reranker) sul corpus reale — verifica del numero
del piano (campagna 2026-06-03: e5-base dense MRR 0.71 / R@10 0.84).

Misura il candidato a punto-di-svolta INTERATTIVO: un dense embedder piu' forte
(intfloat/multilingual-e5-base, 768d) DA SOLO, senza il costo-latency del reranker.
Cosine diretto (bypassa SemanticMemory che e' a 384d) -> e' una MISURA, non un wiring.
Su COPIA del corpus live, 25 query IT etichettate. Hermetic.

Run: python scripts/bench_e5_dense.py   (scarica e5-base ~440MB la 1a volta)
"""
from __future__ import annotations

import os
import shutil
import sqlite3
import sys
import tempfile
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bench_recall_quality import LABELED  # noqa: E402

DENSE = "intfloat/multilingual-e5-base"
DPFX, QPFX = "passage: ", "query: "


def _load() -> tuple[list[str], list[str]]:
    src = os.path.expanduser("~/.engram/semantic/semantic.db")
    dst = os.path.join(tempfile.mkdtemp(prefix="bench_e5_"), "s.db")
    shutil.copy2(src, dst)
    c = sqlite3.connect(f"file:{dst}?mode=ro", uri=True)
    rows = c.execute(
        "SELECT id, proposition FROM facts WHERE superseded_by IS NULL "
        "AND status NOT IN ('quarantined','orphaned') AND length(proposition) > 0"
    ).fetchall()
    c.close()
    return [r[0][:10] for r in rows], [r[1] for r in rows]


def _metrics(ranked: list[list[str]]) -> dict:
    r1 = r5 = r10 = 0
    mrr = 0.0
    for (_, exp), rk in zip(LABELED, ranked, strict=False):
        rank = rk.index(exp) + 1 if exp in rk else 0
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
    ids, props = _load()
    queries = [q for q, _ in LABELED]
    from sentence_transformers import SentenceTransformer

    t0 = time.time()
    m = SentenceTransformer(DENSE, trust_remote_code=True)
    cemb = m.encode([DPFX + p for p in props], normalize_embeddings=True, convert_to_numpy=True,
                    show_progress_bar=False, batch_size=64).astype(np.float32)
    enc = time.time() - t0
    t0 = time.time()
    qemb = m.encode([QPFX + q for q in queries], normalize_embeddings=True, convert_to_numpy=True,
                    show_progress_bar=False, batch_size=64).astype(np.float32)
    q_enc_ms = (time.time() - t0) / len(queries) * 1000
    ranked = [[ids[j] for j in np.argsort(-(qemb[i] @ cemb.T))[:10]] for i in range(len(queries))]
    d = _metrics(ranked)
    print(f"=== e5-base DENSE-ONLY (768d) corpus={len(ids)} | 25 query IT ===", flush=True)
    print(f"e5-base dense : R@1={d['R@1']:.3f} R@5={d['R@5']:.3f} R@10={d['R@10']:.3f} MRR={d['MRR']:.3f}  "
          f"(encode corpus {enc:.0f}s, query-encode {q_enc_ms:.0f}ms/q)", flush=True)
    print(f"vs attuale multilingue-L12 (MRR 0.466 R@10 0.800): dMRR {d['MRR']-0.466:+.3f} dR@10 {d['R@10']-0.800:+.3f}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
