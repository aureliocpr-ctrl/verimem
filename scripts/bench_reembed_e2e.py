#!/usr/bin/env python
"""Validazione END-TO-END del re-embed multilingue sul pipeline recall() REALE.

L'A/B (bench_embedding_ab.py) ha provato il guadagno con cosine in-memory. Qui
verifico che il guadagno REGGA attraverso il path di produzione vero —
``SemanticMemory.recall`` con gate (status/freshness/denylist) + cache + il
filtro v9 per-modello — dopo un re-embed con il modello multilingue.

In piu' VALIDA v9 sotto switch di modello: i fatti re-embeddati vengono stampati
con embedding_model=nuovo; recall (model_signature()=nuovo) li include via
COALESCE; i NON re-embeddati (NULL->_LEGACY=MiniLM != nuovo) verrebbero esclusi
-> per questo si re-embedda TUTTO l'eligible. Se v9 fosse rotto, recall darebbe 0.

Modello: paraphrase-multilingual-MiniLM-L12-v2 (384d, NO prefisso -> compatibile
con verimem.embedding.encode senza modifiche). Su COPIA del corpus live: ZERO
scrittura su ~/.verimem.

Run:  python scripts/bench_reembed_e2e.py
"""
from __future__ import annotations

import os

# DEVE precedere l'import di verimem.config: CONFIG.embedding_model si fissa a
# costruzione. Cosi' encode() E model_signature() usano il modello multilingue.
os.environ["HIPPO_EMBEDDING_MODEL"] = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
os.environ["ENGRAM_RECALL_RERANK"] = "0"  # CE default-ON since 2026-06-10 — e2e re-embed measures the bi-encoder

import sys  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # per import LABELED

import shutil  # noqa: E402
import sqlite3  # noqa: E402
import tempfile  # noqa: E402
from pathlib import Path  # noqa: E402

from bench_recall_quality import LABELED  # stesse 25 query etichettate  # noqa: E402

from verimem import embedding  # noqa: E402
from verimem.semantic import SemanticMemory  # noqa: E402


def main() -> int:
    src = os.path.expanduser("~/.engram/semantic/semantic.db")
    tmp = Path(tempfile.mkdtemp(prefix="bench_e2e_"))
    dst = tmp / "semantic.db"
    shutil.copy2(src, dst)

    # 1) migra la copia (aggiunge embedding_model col v9 se assente)
    SemanticMemory(db_path=dst)
    # 2) re-embedda TUTTO l'eligible col modello attivo (multilingue) + stampa
    con = sqlite3.connect(dst)
    rows = con.execute(
        "SELECT id, proposition FROM facts WHERE superseded_by IS NULL "
        "AND status NOT IN ('quarantined','orphaned') AND length(proposition) > 0"
    ).fetchall()
    ids = [r[0] for r in rows]
    props = [r[1] for r in rows]
    print(f"re-embed di {len(ids)} fatti eligible con {embedding.model_signature()} ...")
    vecs = embedding.encode(props)  # (N, 384) col modello multilingue
    sig = embedding.model_signature()
    for fid, v in zip(ids, vecs, strict=False):
        con.execute(
            "UPDATE facts SET embedding = ?, embedding_model = ? WHERE id = ?",
            (embedding.serialize(v.astype("float32")), sig, fid),
        )
    con.commit()
    con.close()

    # 3) recall via pipeline REALE su istanza fresca (cache ricostruita)
    sm = SemanticMemory(db_path=dst)
    n = len(LABELED)
    r1 = r5 = r10 = 0
    mrr = 0.0
    miss = []
    for q, expected in LABELED:
        hits = sm.recall(q, k=10)
        ranked = [f.id[:10] for f, *_ in hits]
        rank = ranked.index(expected) + 1 if expected in ranked else 0
        if rank == 1:
            r1 += 1
        if 1 <= rank <= 5:
            r5 += 1
        if 1 <= rank <= 10:
            r10 += 1
        if rank:
            mrr += 1.0 / rank
        else:
            miss.append(expected)
    print("=== RE-EMBED END-TO-END (recall() REALE, gate+cache+v9, multilingue) ===")
    print(f"query: {n}  | corpus re-embeddato: {len(ids)}")
    print(f"Recall@1 = {r1}/{n} = {r1/n:.3f}")
    print(f"Recall@5 = {r5}/{n} = {r5/n:.3f}")
    print(f"Recall@10= {r10}/{n} = {r10/n:.3f}")
    print(f"MRR@10   = {mrr/n:.3f}")
    print("BASELINE recall() live (MiniLM EN) era: R@10=0.32 MRR=0.23")
    print(f"miss residui: {len(miss)}  {miss}")
    if r10 == 0:
        print("!!! R@10=0 -> v9 starebbe ESCLUDENDO i fatti re-embeddati (BUG da indagare)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
