"""Tre ordinamenti a confronto sulla stessa popolazione: data, conteggio, IDF.

Il banco gemello ha mostrato che ordinare per NUMERO di token agganciati
peggiora i recenti (14 su 20 -> 4 su 20) quando si cerca per argomento.
Quel criterio conta i token e basta: «senza» pesa quanto «tbook».

Qui il terzo candidato pesa ogni token per la sua RARITA' nel corpus
(inverse document frequency): un token che compare in dieci fatti dice
molto di piu' di uno che ne tocca duemila. Se non batte gli altri due,
la cura sul ranking non va scritta e resta l'avviso.

Sola lettura: mode=ro, solo SELECT.
"""
import math
import re
import sqlite3

from verimem.bm25_rank import _tokens as informativi
from verimem.config import CONFIG

BASE = ("status NOT IN ('orphaned','quarantined','user_belief') "
        "AND superseded_by IS NULL AND status != 'legacy_unverified'")
N = 20


def apri():
    p = str(CONFIG.semantic_db).replace("\\", "/")
    return sqlite3.connect("file:%s?mode=ro" % p, uri=True)


def df(cur, tok, cache):
    """Quanti fatti contengono il token (document frequency), con cache."""
    if tok not in cache:
        cache[tok] = cur.execute(
            "SELECT COUNT(*) FROM facts WHERE %s AND LOWER(proposition) LIKE ?" % BASE,
            ("%%%s%%" % tok,)).fetchone()[0]
    return cache[tok]


def candidati(cur, toks, q):
    for ramo in ("AND", "OR"):
        t = toks if ramo == "AND" else ([x for x in informativi(q) if len(x) >= 2] or toks)
        join = " AND " if ramo == "AND" else " OR "
        where = ("LOWER(proposition) LIKE ?" if len(t) == 1
                 else "(" + join.join(["LOWER(proposition) LIKE ?"] * len(t)) + ")")
        sql = ("SELECT id, LOWER(proposition) FROM facts WHERE %s AND %s "
               "ORDER BY created_at DESC" % (where, BASE))
        righe = cur.execute(sql, tuple("%%%s%%" % x for x in t)).fetchall()
        if righe:
            return righe, t
    return [], toks


def main():
    con = apri()
    cur = con.cursor()
    tot = cur.execute("SELECT COUNT(*) FROM facts WHERE %s" % BASE).fetchone()[0]
    cache = {}
    print("corpus servibile: %d - query = parole del TOPIC - n=%d per fascia" % (tot, N))
    print("%-8s %6s %9s %10s %8s %10s" % (
        "fascia", "usati", "per data", "per conto", "per IDF", "mai cand."))
    for nome, ordine, off in (
            ("recenti", "DESC", 0), ("medi", "DESC", tot // 2), ("vecchi", "ASC", 0)):
        sql = ("SELECT id, proposition, topic FROM facts WHERE %s ORDER BY created_at %s "
               "LIMIT %d OFFSET %d" % (BASE, ordine, N * 3, off))
        usati = d5 = c5 = i5 = persi = 0
        for fid, prop, topic in cur.execute(sql).fetchall():
            if usati >= N:
                break
            parole = [w for w in re.split(r"[/\-_\s]+", (topic or "").lower()) if len(w) >= 3]
            if len(parole) < 2:
                continue
            q = " ".join(parole)
            righe, t = candidati(cur, parole, q)
            if not righe:
                continue
            usati += 1
            ids_data = [r[0] for r in righe]
            if fid in ids_data[:5]:
                d5 += 1
            if fid not in ids_data:
                persi += 1
            peso = {x: math.log(1.0 + tot / max(1.0, df(cur, x, cache))) for x in t}
            def conto(r):
                return sum(1 for x in t if x in r[1])
            def idf(r):
                return sum(peso[x] for x in t if x in r[1])
            if fid in [r[0] for r in sorted(righe, key=conto, reverse=True)][:5]:
                c5 += 1
            if fid in [r[0] for r in sorted(righe, key=idf, reverse=True)][:5]:
                i5 += 1
        print("%-8s %6d %9d %10d %8d %10d" % (nome, usati, d5, c5, i5, persi))
    con.close()


if __name__ == "__main__":
    main()
