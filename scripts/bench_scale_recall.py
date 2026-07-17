"""Scale bench: latency del recall + memoria vs dimensione del corpus N.

Testa il rischio flaggato da agy: la matrice di embedding IN-MEMORY è O(N) ->
latency/OOM a scala. Usa vettori random unit SINTETICI (salta il costo encode: il
comportamento matrix/cosine/sort + memoria è identico a prescindere dal contenuto
del vettore). Misura: tempo di popolamento, cold-recall (build matrice), warm
p50/p95, RSS del processo e delta-RSS della matrice.

Hermetic: DB temporaneo, MAI ~/.verimem. Standalone (come bench_recall_quality).
Run: python scripts/bench_scale_recall.py
"""
from __future__ import annotations

import gc
import os

os.environ.setdefault(
    "HIPPO_EMBEDDING_MODEL",
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
)
os.environ["ENGRAM_RECALL_RERANK"] = "0"  # CE default-ON since 2026-06-10 — scaling/latency of the bi-encoder path

import sqlite3  # noqa: E402
import tempfile  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402
import psutil  # noqa: E402

from verimem import embedding as emb  # noqa: E402
from verimem.semantic import SemanticMemory  # noqa: E402

DIM = 384
_rng = np.random.default_rng(1234)


def rss_mb() -> float:
    return psutil.Process().memory_info().rss / 1024 / 1024


def bulk_insert(db_path: Path, start: int, count: int, sig: str) -> None:
    vecs = _rng.standard_normal((count, DIM)).astype(np.float32)
    vecs /= np.linalg.norm(vecs, axis=1, keepdims=True) + 1e-9
    now = time.time()
    rows = [
        (
            f"f{start + i:08d}", f"fatto sintetico scale {start + i} lorem ipsum dolor sit",
            "scale/test", 0.5, "[]", now, emb.serialize(vecs[i]), sig, "model_claim",
        )
        for i in range(count)
    ]
    conn = sqlite3.connect(db_path)
    try:
        conn.executemany(
            "INSERT OR REPLACE INTO facts(id, proposition, topic, confidence, "
            "source_episodes, created_at, embedding, embedding_model, status) "
            "VALUES(?,?,?,?,?,?,?,?,?)",
            rows,
        )
        conn.commit()
    finally:
        conn.close()


def main() -> int:
    tmp = Path(tempfile.mkdtemp()) / "scale.db"
    SemanticMemory(db_path=tmp)  # crea lo schema
    sig = emb.model_signature()
    emb.encode("warmup del modello")  # esclude il model-load dal timing per-N

    targets = [1000, 5000, 10000, 50000, 100000]
    print(f"modello attivo: {sig}")
    print(f"{'N':>8} {'pop_s':>7} {'cold_s':>7} {'p50_ms':>7} {'p95_ms':>7} {'rss_mb':>7} {'dRSS_mb':>7}")
    cur = 0
    for N in targets:
        bulk_insert(tmp, cur, N - cur, sig)
        cur = N
        gc.collect()
        sm = SemanticMemory(db_path=tmp)  # fresh -> cache corpus in-process vuota
        rss0 = rss_mb()
        t0 = time.time()
        sm.recall("query di prova scale", k=10)  # cold: costruisce la matrice O(N)
        cold = time.time() - t0
        rss1 = rss_mb()
        lat = []
        for q in range(30):
            t0 = time.time()
            sm.recall(f"query numero {q} scale test", k=10)
            lat.append((time.time() - t0) * 1000)
        lat.sort()
        p50 = lat[len(lat) // 2]
        p95 = lat[min(len(lat) - 1, int(len(lat) * 0.95))]
        # tempo di popolamento di QUESTO incremento misurato a parte
        print(f"{N:>8} {'-':>7} {cold:>7.3f} {p50:>7.1f} {p95:>7.1f} {rss1:>7.0f} {rss1 - rss0:>7.1f}")
        del sm
    print("DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
