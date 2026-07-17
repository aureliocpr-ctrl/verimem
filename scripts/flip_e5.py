#!/usr/bin/env python
"""FLIP a intfloat/multilingual-e5-base (768d) — TUTTE le superfici.

facts: re-embed con ``as_passage`` (recall usa ``as_query``, wired in semantic.recall).
episodi/skill: re-embed PLAIN sotto e5 (store/recall NON prefix-wired -> coerente
entrambi i lati; e5-base >= L12 anche senza prefisso). DG ricalcolato a dim=768.

``--live`` fa BACKUP dei 3 DB prima di scrivere. Senza ``--live`` opera sulla data_dir
passata (usare una COPIA per il dry-verify). VERIFY: facts recall (25 query IT etichettate,
path reale con as_query) -> MRR; sanity episodi/skill recall non-vuoti.

Run dry:  python scripts/flip_e5.py <copia_data_dir>
Run live: python scripts/flip_e5.py ~/.engram --live   (poi restart MCP)
"""
from __future__ import annotations

import os

_E5 = "intfloat/multilingual-e5-base"
os.environ["HIPPO_EMBEDDING_MODEL"] = _E5
os.environ["HIPPO_EMBEDDING_DIM"] = "768"

import shutil  # noqa: E402
import sqlite3  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402


def _ensure_col(db_path, table) -> None:
    """ALTER difensivo: garantisce la colonna embedding_model (drift ledger/schema)."""
    c = sqlite3.connect(db_path)
    try:
        cols = {r[1] for r in c.execute(f"PRAGMA table_info({table})")}
        if "embedding_model" not in cols:
            c.execute(f"ALTER TABLE {table} ADD COLUMN embedding_model TEXT")
            c.commit()
            print(f"  [schema-fix] embedding_model aggiunta a {table} ({Path(db_path).name})")
    finally:
        c.close()


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: flip_e5.py <data_dir> [--live]")
        return 2
    data_dir = Path(sys.argv[1]).expanduser()
    live = "--live" in sys.argv[2:]
    sem = data_dir / "semantic" / "semantic.db"
    epi = data_dir / "episodes" / "episodes.db"
    ski = data_dir / "skills" / "skills_index.db"
    ski_dir = data_dir / "skills"
    for p in (sem, epi, ski):
        if not p.exists():
            print(f"MISSING {p} -> abort")
            return 2

    from verimem import embedding
    from verimem.config import CONFIG
    from verimem.dentate_gyrus import dg_encode
    from verimem.memory import EpisodicMemory, _dg_serialize, _global_dg_projection
    from verimem.semantic import SemanticMemory
    from verimem.skill import SkillLibrary

    sig = embedding.model_signature()
    print(f"=== FLIP e5 ===  dir={data_dir}  LIVE={live}  model={sig}  dim={CONFIG.embedding_dim}", flush=True)
    if sig != _E5:
        print(f"!! model_signature ({sig}) != {_E5} -> abort")
        return 2
    ok, actual = embedding.verify_model_dim()
    print(f"dim check: actual={actual} expected={CONFIG.embedding_dim} ok={ok}", flush=True)
    if not ok:
        print("!! dim mismatch -> abort (no write)")
        return 2

    # migra schema + ALTER difensivo embedding_model
    SemanticMemory(db_path=sem)
    EpisodicMemory(epi)
    SkillLibrary(dir_path=ski_dir, db_path=ski)
    _ensure_col(sem, "facts")
    _ensure_col(epi, "episodes")
    _ensure_col(ski, "skills")

    if live:
        bdir = Path(os.path.expanduser("~/.engram/backups"))
        bdir.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y%m%d-%H%M%S")
        for p, name in ((sem, "semantic"), (epi, "episodes"), (ski, "skills_index")):
            b = bdir / f"{name}.pre-e5-{ts}.db"
            shutil.copy2(p, b)
            print(f"BACKUP {p.name} -> {b}", flush=True)

    # --- FACTS: re-embed con as_passage ---
    con = sqlite3.connect(sem)
    rows = con.execute(
        "SELECT id, proposition FROM facts WHERE superseded_by IS NULL "
        "AND status NOT IN ('quarantined','orphaned') AND length(proposition) > 0"
    ).fetchall()
    if rows:
        vecs = embedding.encode([embedding.as_passage(r[1]) for r in rows])
        for (fid, _), v in zip(rows, vecs, strict=False):
            con.execute("UPDATE facts SET embedding = ?, embedding_model = ? WHERE id = ?",
                        (embedding.serialize(v.astype("float32")), sig, fid))
        con.commit()
    con.close()
    print(f"facts re-embedded (e5, as_passage): {len(rows)}", flush=True)

    # --- EPISODI: summary plain + dg ricalcolato @768 + context NULL ---
    mem = EpisodicMemory(epi)
    eps = mem.all()
    proj = _global_dg_projection()
    con = sqlite3.connect(epi)
    for ep in eps:
        e = embedding.encode(ep.summary())  # plain (episodi non prefix-wired)
        dgb = _dg_serialize(dg_encode(e, proj, k_sparse=CONFIG.dg_k_sparse))
        con.execute(
            "UPDATE episodes SET summary_embedding = ?, dg_embedding = ?, "
            "context_embedding = NULL, embedding_model = ? WHERE id = ?",
            (embedding.serialize(e.astype("float32")), dgb, sig, ep.id),
        )
    con.commit()
    con.close()
    print(f"episodi re-embedded (e5, plain, dg@{CONFIG.embedding_dim}): {len(eps)}", flush=True)

    # --- SKILL: lib.store re-encoda il trigger (plain) ---
    lib = SkillLibrary(dir_path=ski_dir, db_path=ski)
    sk = lib.all()
    for s in sk:
        lib.store(s)
    print(f"skill re-embedded (e5, plain): {len(sk)}", flush=True)

    # --- VERIFY facts (path reale, as_query) + sanity episodi/skill ---
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from bench_recall_quality import LABELED
    sm = SemanticMemory(db_path=sem)
    n = len(LABELED)
    r1 = r5 = r10 = 0
    mrr = 0.0
    for q, exp in LABELED:
        ranked = [f.id[:10] for f, *_ in sm.recall(q, k=10)]
        rank = ranked.index(exp) + 1 if exp in ranked else 0
        if rank == 1:
            r1 += 1
        if 1 <= rank <= 5:
            r5 += 1
        if 1 <= rank <= 10:
            r10 += 1
            mrr += 1.0 / rank
    print(f"VERIFY facts (e5, as_query): R@1={r1/n:.3f} R@5={r5/n:.3f} R@10={r10/n:.3f} "
          f"MRR={mrr/n:.3f}  (L12 live=0.466)", flush=True)
    try:
        er = EpisodicMemory(epi).recall("engram memory loop recall", k=3)
        print(f"sanity episodi recall: {len(er)} hit (>0 = ok)", flush=True)
        sr = SkillLibrary(dir_path=ski_dir, db_path=ski).retrieve("memory recall", k=3)
        print(f"sanity skill retrieve: {len(sr)} hit (>0 = ok)", flush=True)
    except Exception as e:  # noqa: BLE001
        print(f"sanity SKIP: {e}", flush=True)
    print("DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
