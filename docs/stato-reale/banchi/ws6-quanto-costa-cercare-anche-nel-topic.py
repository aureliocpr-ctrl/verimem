"""Quanto costa cercare anche nel topic? Predizione: MENO, non di piu'.

Il LIKE su due colonne raddoppia i parametri, ma fa RIUSCIRE il ramo AND
ed evita il ripiego OR, che oggi aggancia migliaia di righe e le ordina
tutte. Se la predizione regge, la variante piu' completa e' anche la piu'
economica.

Non e' un benchmark del prodotto: e' SQL che replica la porta.
Sola lettura: mode=ro, solo SELECT.
"""
import re
import sqlite3
import time

from verimem.bm25_rank import _tokens as informativi
from verimem.config import CONFIG

BASE = ("status NOT IN ('orphaned','quarantined','user_belief') "
        "AND superseded_by IS NULL AND status != 'legacy_unverified'")
N = 20


def apri():
    p = str(CONFIG.semantic_db).replace("\\", "/")
    return sqlite3.connect("file:%s?mode=ro" % p, uri=True)


def cerca(cur, toks, q, campi):
    """Replica la porta e restituisce (n_risultati, ramo_usato)."""
    for ramo in ("AND", "OR"):
        t = toks if ramo == "AND" else ([x for x in informativi(q) if len(x) >= 2] or toks)
        join = " AND " if ramo == "AND" else " OR "
        if campi == "p":
            uno, n_par = "LOWER(proposition) LIKE ?", 1
        else:
            uno, n_par = "(LOWER(proposition) LIKE ? OR LOWER(topic) LIKE ?)", 2
        where = "(" + join.join([uno] * len(t)) + ")"
        par = []
        for x in t:
            par.extend(["%%%s%%" % x] * n_par)
        sql = ("SELECT id FROM facts WHERE %s AND %s ORDER BY created_at DESC"
               % (where, BASE))
        ids = [r[0] for r in cur.execute(sql, tuple(par))]
        if ids:
            return len(ids), ramo
    return 0, "zero"


def main():
    con = apri()
    cur = con.cursor()
    tot = cur.execute("SELECT COUNT(*) FROM facts WHERE %s" % BASE).fetchone()[0]
    print("corpus servibile: %d - n=%d per fascia - tempi in millisecondi" % (tot, N))
    print("%-8s | %8s %8s %6s | %8s %8s %6s | %s" % (
        "fascia", "P med", "P max", "ramo", "P+T med", "P+T max", "ramo", "verdetto"))
    for nome, ordine, off in (
            ("recenti", "DESC", 0), ("medi", "DESC", tot // 2), ("vecchi", "ASC", 0)):
        sql = ("SELECT id, topic FROM facts WHERE %s ORDER BY created_at %s "
               "LIMIT %d OFFSET %d" % (BASE, ordine, N * 3, off))
        usati = 0
        tp, tt = [], []
        rami_p, rami_t = {}, {}
        for _fid, topic in cur.execute(sql).fetchall():
            if usati >= N:
                break
            parole = [w for w in re.split(r"[/\-_\s]+", (topic or "").lower()) if len(w) >= 3]
            if len(parole) < 2:
                continue
            usati += 1
            q = " ".join(parole)
            t0 = time.perf_counter()
            _n, r = cerca(cur, parole, q, "p")
            tp.append((time.perf_counter() - t0) * 1000)
            rami_p[r] = rami_p.get(r, 0) + 1
            t0 = time.perf_counter()
            _n, r = cerca(cur, parole, q, "pt")
            tt.append((time.perf_counter() - t0) * 1000)
            rami_t[r] = rami_t.get(r, 0) + 1
        mp = sorted(tp)[len(tp) // 2]
        mt = sorted(tt)[len(tt) // 2]
        verdetto = "P+T piu' veloce" if mt < mp else "P+T piu' lenta"
        print("%-8s | %8.1f %8.1f %6s | %8.1f %8.1f %6s | %s" % (
            nome, mp, max(tp), max(rami_p, key=rami_p.get),
            mt, max(tt), max(rami_t, key=rami_t.get), verdetto))
    con.close()


if __name__ == "__main__":
    main()
