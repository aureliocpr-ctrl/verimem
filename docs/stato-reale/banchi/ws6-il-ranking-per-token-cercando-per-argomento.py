"""Il caso realistico: cerco per ARGOMENTO, non con le parole del fatto.

Il banco gemello costruiva la query dalle parole della proposition, quindi
il fatto giusto vinceva per costruzione. Qui la query sono le parole del
`topic` — che chi salva scrive separatamente dal testo — spezzate sui
separatori. E' come si cerca davvero: si ricorda l'argomento, non la frase.

Sola lettura: mode=ro, solo SELECT.
"""
import re
import sqlite3

from verimem.bm25_rank import _tokens as informativi
from verimem.config import CONFIG

BASE = ("status NOT IN ('orphaned','quarantined','user_belief') "
        "AND superseded_by IS NULL AND status != 'legacy_unverified'")
N = 20


def apri():
    p = str(CONFIG.semantic_db).replace("\\", "/")
    return sqlite3.connect(f"file:{p}?mode=ro", uri=True)


def candidati(cur, toks, q):
    for ramo in ("AND", "OR"):
        t = toks if ramo == "AND" else ([x for x in informativi(q) if len(x) >= 2] or toks)
        join = " AND " if ramo == "AND" else " OR "
        where = ("LOWER(proposition) LIKE ?" if len(t) == 1
                 else "(" + join.join(["LOWER(proposition) LIKE ?"] * len(t)) + ")")
        sql = (f"SELECT id, LOWER(proposition) FROM facts WHERE {where} AND {BASE} "
               "ORDER BY created_at DESC")
        righe = cur.execute(sql, tuple(f"%{x}%" for x in t)).fetchall()
        if righe:
            return righe, t, ramo
    return [], toks, "zero"


def main():
    con = apri()
    cur = con.cursor()
    tot = cur.execute(f"SELECT COUNT(*) FROM facts WHERE {BASE}").fetchone()[0]
    print("corpus servibile: %d · query = parole del TOPIC · n=%d per fascia" % (tot, N))
    print("%-8s %6s %9s %10s %11s %10s" % (
        "fascia", "usati", "per data", "per token", "mai cand.", "candidati"))
    for nome, ordine, off in (
            ("recenti", "DESC", 0), ("medi", "DESC", tot // 2), ("vecchi", "ASC", 0)):
        sql = ("SELECT id, proposition, topic FROM facts WHERE %s ORDER BY created_at %s "
               "LIMIT %d OFFSET %d" % (BASE, ordine, N * 3, off))
        usati = d5 = t5 = persi = 0
        ncand = []
        for fid, prop, topic in cur.execute(sql).fetchall():
            if usati >= N:
                break
            parole = [w for w in re.split(r"[/\-_\s]+", (topic or "").lower())
                      if len(w) >= 3]
            if len(parole) < 2:
                continue
            q = " ".join(parole)
            righe, t, _r = candidati(cur, parole, q)
            if not righe:
                continue
            usati += 1
            ncand.append(len(righe))
            ids_data = [r[0] for r in righe]
            if fid in ids_data[:5]:
                d5 += 1
            def quanti(r):
                return sum(1 for x in t if x in r[1])
            ids_tok = [r[0] for r in sorted(righe, key=quanti, reverse=True)]
            if fid in ids_tok[:5]:
                t5 += 1
            if fid not in ids_data:
                persi += 1
        medc = sorted(ncand)[len(ncand) // 2] if ncand else 0
        print("%-8s %6d %9d %10d %11d %10d" % (nome, usati, d5, t5, persi, medc))
    con.close()


if __name__ == "__main__":
    main()
