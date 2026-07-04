#!/usr/bin/env python
"""Benchmark self-retrieval ~300 probe (potenza statistica) su COPIA corpus Engram.

PERCHE': il bench labeled n=25 (``bench_recall_quality.py``) e' troppo piccolo —
l'IC Wilson contiene il baseline, quindi il delta centering misurato la' (R@10
0.84->0.88) NON e' statisticamente risolvibile. Qui campioniamo ~300 fatti reali,
generiamo una query con riformulazione DETERMINISTICA (sottostringa: meta' /
drop-head / seconda-meta'), gold = il fact_id sorgente, e misuriamo R@1/R@10/MRR
via ``SemanticMemory.recall`` con ``ENGRAM_RECALL_CENTERING`` OFF poi ON sullo
STESSO set di probe (campione APPAIATO).

ONESTA' (A4, niente marketing):
  - query = SOTTOSTRINGHE del fatto, NON parafrasi LLM: resta overlap lessicale,
    quindi il R assoluto e' OTTIMISTICO vs query davvero parafrasate. Il valore di
    questo bench e' il DELTA centering e la POTENZA (n~300), non la cifra assoluta.
  - gate reali (status / freshness v8 / modello-embedding v9) sono attivi dentro
    recall: un gold gate-escluso conta come miss. R@50 stima quanti si recuperano
    affatto (ranking vs gate).
  - OFF vs ON = STESSO set -> il test corretto e' McNemar (proporzioni appaiate),
    riportato OLTRE al Wilson IC su ciascuna condizione (richiesto dal task).
  - lo status 'user_manual' citato nel task NON esiste nell'enum reale
    (_VALID_STATUSES); campioniamo l'intersezione presente nel corpus.

Sicurezza: gira su una COPIA del db (SemanticMemory.__init__ esegue migrazioni =
WRITE). ZERO scrittura sul corpus live ~/.engram.

Run:  python scripts/bench_recall_self.py
"""
from __future__ import annotations

import math
import os
import random
import shutil
import sqlite3
import tempfile
import time
from pathlib import Path

# Encode budget generoso: il bench fa ~600 encode di query; senza questo, un
# encoder freddo/contended farebbe scattare il fallback keyword di recall
# (q_emb=None) falsando la misura semantica. 60s e' largo, mai raggiunto a caldo.
os.environ.setdefault("HIPPO_RECALL_ENCODE_BUDGET_S", "60")
# CE rerank default-ON since 2026-06-10: this module both benches the plain
# bi-encoder AND provides the shared machinery (_copy_live_db & co.) for the
# paired rerank benches — pin OFF at import; arm-flipping benches override.
os.environ["ENGRAM_RECALL_RERANK"] = "0"

from engram.semantic import _VALID_STATUSES, SemanticMemory  # noqa: E402

SEED = 1234
N_TARGET = 300
MIN_WORDS = 10
K_DEEP = 50
# Status richiesti dal task (user_manual incluso volutamente per fedelta'; se non
# esiste nell'enum reale viene semplicemente non-matchato dalla query SQL).
SAMPLE_STATUSES = ("verified", "user_manual", "model_claim", "provisional")


def _copy_live_db() -> Path:
    src = Path(os.path.expanduser("~/.engram/semantic/semantic.db"))
    tmp = Path(tempfile.mkdtemp(prefix="bench_self_"))
    dst = tmp / "semantic.db"
    for ext in ("", "-wal", "-shm"):
        s = Path(str(src) + ext)
        if s.exists():
            shutil.copy2(s, str(dst) + ext)
    return dst


def _wilson(x: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """IC95% di Wilson score per una proporzione x/n."""
    if n == 0:
        return (0.0, 0.0)
    p = x / n
    denom = 1.0 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def _mcnemar(b: int, c: int) -> tuple[float, float]:
    """McNemar continuity-corrected su coppie discordanti.

    b = OFF-hit & ON-miss; c = OFF-miss & ON-hit. p-value = chi2(1 dof) survival.
    """
    if b + c == 0:
        return (0.0, 1.0)
    stat = (abs(b - c) - 1) ** 2 / (b + c)
    p = math.erfc(math.sqrt(stat / 2.0))
    return (stat, p)


# Stopword IT+EN per la suite "hard": rimuovendo i connettivi e rimescolando le
# content-word la query perde la sequenza fluente del fatto -> esce dal regime
# saturato della sottostringa contigua (R@10~0.99) verso il regime difficile dove
# il centering era stato osservato agire (n=25: R@10 0.84). NON e' parafrasi LLM
# (manterrebbe il non-determinismo + costo): e' un proxy deterministico di "query
# a parole chiave con parole proprie", il caso d'uso reale.
_STOP = set(
    "di a da in con su per tra fra il lo la i gli le un uno una e ed o od ma se che "
    "chi cui non come dove quando perche piu meno del dello della dei degli delle al "
    "allo alla ai agli alle dal col sul nel suo sua suoi sue questo questa quello "
    "the of to and in a is it that for on with as are be this an or at by from "
    "was were has have had not but its their his her our your".split()
)


def _make_query(prop: str, kind: int) -> str:
    """Riformulazione DETERMINISTICA non-banale (NON copia integrale) — suite EASY."""
    words = prop.split()
    n = len(words)
    if kind == 0:                       # prima meta'
        return " ".join(words[: max(5, n // 2)])
    if kind == 1:                       # togli le prime ~4 parole (perde il soggetto)
        return " ".join(words[4:]) or prop
    return " ".join(words[n // 2:]) or prop   # seconda meta'


def _make_query_hard(prop: str, fid: str) -> str:
    """Suite HARD: keyword-bag di content-word rimescolate (no stopword/connettivi).

    Seed deterministico dall'id (hex) -> riproducibile. Riduce l'overlap di
    sequenza per spingere il recall fuori dall'effetto soffitto.
    """
    toks = [w.strip(".,;:()[]{}\"'`") for w in prop.split()]
    content = [w for w in toks if len(w) >= 3 and w.lower() not in _STOP]
    if len(content) < 4:                # fatto troppo corto -> fallback su tutto
        content = [w for w in toks if w]
    rng = random.Random(int(fid[:8], 16))
    if len(content) > 8:                # mantieni ~8 content-word sparse
        content = rng.sample(content, 8)
    rng.shuffle(content)                # rompi la sequenza originale
    return " ".join(content) or prop


def _sample_facts(dst: Path) -> list[tuple[str, str]]:
    """Campiona ~300 fatti (id, proposition) recallable dalla COPIA (seed fisso)."""
    placeholders = ",".join("?" for _ in SAMPLE_STATUSES)
    conn = sqlite3.connect(str(dst))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        f"SELECT id, proposition FROM facts "
        f"WHERE superseded_by IS NULL AND status IN ({placeholders})",
        SAMPLE_STATUSES,
    ).fetchall()
    conn.close()
    pool = [
        (r["id"], r["proposition"])
        for r in rows
        if r["proposition"] and len(r["proposition"].split()) >= MIN_WORDS
    ]
    rng = random.Random(SEED)
    rng.shuffle(pool)
    return pool[:N_TARGET]


def _run(sm: SemanticMemory, probes: list[tuple[str, str]], centering: bool) -> dict:
    os.environ["ENGRAM_RECALL_CENTERING"] = "on" if centering else "0"
    r1 = r10 = r50 = 0
    mrr = 0.0
    hit10: list[int] = []
    for q, gold in probes:
        hits = sm.recall(q, k=K_DEEP)
        ids = [f.id for f, *_ in hits]
        rank = ids.index(gold) + 1 if gold in ids else 0
        if rank == 1:
            r1 += 1
        if 1 <= rank <= 10:
            r10 += 1
            mrr += 1.0 / rank
        if 1 <= rank <= 50:
            r50 += 1
        hit10.append(1 if 1 <= rank <= 10 else 0)
    n = len(probes)
    return {"n": n, "r1": r1, "r10": r10, "r50": r50,
            "mrr": mrr / n if n else 0.0, "hit10": hit10}


def _report(sm: SemanticMemory, label: str, probes: list[tuple[str, str]]) -> bool:
    """Misura OFF vs ON su `probes`, stampa tabella + Wilson + McNemar. Ritorna
    True se il centering risulta significativo (McNemar p<0.05)."""
    n = len(probes)
    off = _run(sm, probes, centering=False)
    on = _run(sm, probes, centering=True)
    b = sum(1 for o, x in zip(off["hit10"], on["hit10"], strict=False) if o == 1 and x == 0)
    c = sum(1 for o, x in zip(off["hit10"], on["hit10"], strict=False) if o == 0 and x == 1)
    stat, pval = _mcnemar(b, c)
    w_off, w_on = _wilson(off["r10"], n), _wilson(on["r10"], n)
    overlap = not (w_off[1] < w_on[0] or w_on[1] < w_off[0])
    print(f"\n--- SUITE {label}  (n={n}) ---")
    print(f"{'metrica':<10}{'OFF':>10}{'ON':>10}{'delta':>10}")
    for key, lbl in (("r1", "R@1"), ("r10", "R@10"), ("r50", "R@50")):
        vo, vn = off[key] / n, on[key] / n
        print(f"{lbl:<10}{vo:>10.3f}{vn:>10.3f}{vn - vo:>+10.3f}")
    print(f"{'MRR@10':<10}{off['mrr']:>10.3f}{on['mrr']:>10.3f}"
          f"{on['mrr'] - off['mrr']:>+10.3f}")
    print(f"R@10 Wilson IC95%  OFF=[{w_off[0]:.3f},{w_off[1]:.3f}]  "
          f"ON=[{w_on[0]:.3f},{w_on[1]:.3f}]  -> IC "
          f"{'SOVRAPPOSTI' if overlap else 'DISGIUNTI'}")
    sig = pval < 0.05
    print(f"McNemar R@10 (paired): b(OFF+/ON-)={b}  c(OFF-/ON+)={c}  "
          f"chi2={stat:.3f}  p={pval:.4f}  -> centering {'SIGNIFICATIVO' if sig else 'NON significativo'}")
    return sig


def main() -> int:
    t0 = time.time()
    missing = [s for s in SAMPLE_STATUSES if s not in _VALID_STATUSES]
    dst = _copy_live_db()
    sm = SemanticMemory(db_path=dst)  # migrazioni sulla COPIA
    facts = _sample_facts(dst)
    n = len(facts)
    if n == 0:
        print("NESSUN probe campionato — pool vuoto coi criteri dati.")
        return 1
    probes_easy = [(_make_query(p, i % 3), fid) for i, (fid, p) in enumerate(facts)]
    probes_hard = [(_make_query_hard(p, fid), fid) for fid, p in facts]
    # warm-up: carica encoder + corpus cache prima di misurare (no fallback keyword)
    sm.recall("warm up the encoder and the corpus cache please", k=5)

    print("=== BENCH SELF-RETRIEVAL n~300 (COPIA corpus live, query det.) ===")
    if missing:
        print(f"NOTA A1: status del task inesistenti nell'enum, ignorati: {missing}")
        print(f"         (status validi reali: {sorted(_VALID_STATUSES)})")
    print(f"fatti campionati n={n}  k_deep={K_DEEP}  seed={SEED}")
    print("EASY = sottostringa contigua (meta'/drop-head/2a-meta'); "
          "HARD = keyword-bag content-word rimescolate.")
    sig_easy = _report(sm, "EASY (sottostringa)", probes_easy)
    sig_hard = _report(sm, "HARD (keyword-bag)", probes_hard)

    dt = time.time() - t0
    print(f"\n=== VERDETTO (tempo {dt:.1f}s) ===")
    print(f"Centering significativo a n={n}?  EASY: {'SI' if sig_easy else 'NO'}  |  "
          f"HARD: {'SI' if sig_hard else 'NO'}  (criterio McNemar p<0.05)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
