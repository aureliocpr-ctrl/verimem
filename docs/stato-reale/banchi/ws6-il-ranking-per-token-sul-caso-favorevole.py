"""Un ordinamento per pertinenza servirebbe? La colonna in piu' sul banco P2.

P2 ha misurato che una sola parola sbagliata manda i fatti medi e vecchi
fuori dai primi cinque (0 su 20), perche' i candidati escono in ordine di
data. Qui la stessa identica popolazione viene riordinata per NUMERO DI
TOKEN AGGANCIATI, e si conta quanti rientrano.

Predizione dichiarata prima di eseguire: medi e vecchi devono risalire da
0/20 a piu' di 10/20. Se non risalgono, la cura sul percorso caldo non
serve e non va scritta.

Sola lettura: mode=ro, solo SELECT.
"""
import sqlite3

from verimem.bm25_rank import _tokens as informativi
from verimem.config import CONFIG

BASE = ("status NOT IN ('orphaned','quarantined','user_belief') "
        "AND superseded_by IS NULL AND status != 'legacy_unverified'")
N = 20
PAROLE = 8
INTRUSE = ["grounding", "layer", "fonte", "claim", "gate", "giovedi"]


def apri():
    p = str(CONFIG.semantic_db).replace("\\", "/")
    return sqlite3.connect(f"file:{p}?mode=ro", uri=True)


def candidati(cur, toks_and, q_completa):
    """Replica la porta: AND su tutti i token, se zero ripiego OR."""
    for ramo in ("AND", "OR"):
        toks = toks_and if ramo == "AND" else (
            [t for t in informativi(q_completa) if len(t) >= 2] or toks_and)
        join = " AND " if ramo == "AND" else " OR "
        if len(toks) == 1:
            where = "LOWER(proposition) LIKE ?"
        else:
            where = "(" + join.join(["LOWER(proposition) LIKE ?"] * len(toks)) + ")"
        sql = (f"SELECT id, LOWER(proposition) FROM facts WHERE {where} AND {BASE} "
               "ORDER BY created_at DESC")
        righe = cur.execute(sql, tuple(f"%{t}%" for t in toks)).fetchall()
        if righe:
            return righe, toks
    return [], toks_and


def main():
    con = apri()
    cur = con.cursor()
    tot = cur.execute(f"SELECT COUNT(*) FROM facts WHERE {BASE}").fetchone()[0]
    print("corpus servibile: %d · una parola sbagliata · n=%d per fascia" % (tot, N))
    print("%-8s %8s %10s %12s %12s" % (
        "fascia", "per data", "per token", "pos.mediana", "candidati"))
    for nome, ordine, off in (
            ("recenti", "DESC", 0), ("medi", "DESC", tot // 2), ("vecchi", "ASC", 0)):
        sql = ("SELECT id, proposition FROM facts WHERE %s ORDER BY created_at %s "
               "LIMIT %d OFFSET %d" % (BASE, ordine, N, off))
        top5_data = top5_tok = 0
        pos_tok, ncand = [], []
        for fid, prop in cur.execute(sql).fetchall():
            testo = (prop or "").lower()
            q = " ".join((prop or "").split()[:PAROLE])
            toks = [t for t in q.lower().split() if len(t) >= 2]
            intrusa = next((w for w in INTRUSE if w not in testo), None)
            if not toks or intrusa is None:
                continue
            righe, usati = candidati(cur, toks + [intrusa], q + " " + intrusa)
            ids_data = [r[0] for r in righe]
            if fid in ids_data[:5]:
                top5_data += 1
            # riordino per numero di token agganciati (decrescente), stabile
            def quanti(r):
                return sum(1 for t in usati if t in r[1])
            ids_tok = [r[0] for r in sorted(righe, key=quanti, reverse=True)]
            if fid in ids_tok[:5]:
                top5_tok += 1
            pos_tok.append(ids_tok.index(fid) if fid in ids_tok else -1)
            ncand.append(len(righe))
        vis = [p for p in pos_tok if p >= 0]
        med = sorted(vis)[len(vis) // 2] if vis else -1
        medc = sorted(ncand)[len(ncand) // 2] if ncand else 0
        print("%-8s %8d %10d %12d %12d" % (nome, top5_data, top5_tok, med, medc))
    con.close()


if __name__ == "__main__":
    main()
