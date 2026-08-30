"""Cercare anche nel campo topic: quanto cambia il numero di CANDIDATI.

La porta di ricerca fa LIKE solo su `proposition`. Ma il campo che lega un
fatto al suo argomento e' `topic`, e una domanda per argomento non trova
quelle parole nel testo: per questo diciotto fatti vecchi su venti non
entrano nemmeno fra i candidati.

ATTENZIONE ALLA CIRCOLARITA': la query qui e' fatta con le parole del
topic, quindi cercare nel topic trova per costruzione. Il numero che NON
e' circolare e' quanti CANDIDATI produce ciascuna variante: se cercare nel
topic li porta da migliaia a poche decine, l'ordinamento smette di
decidere, ed e' quello il punto.

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
    return sqlite3.connect("file:%s?mode=ro" % p, uri=True)


def cerca(cur, toks, q, campi):
    """campi: 'p' solo proposition, 'pt' proposition o topic."""
    for ramo in ("AND", "OR"):
        t = toks if ramo == "AND" else ([x for x in informativi(q) if len(x) >= 2] or toks)
        join = " AND " if ramo == "AND" else " OR "
        if campi == "p":
            uno = "LOWER(proposition) LIKE ?"
            n_par = 1
        else:
            uno = "(LOWER(proposition) LIKE ? OR LOWER(topic) LIKE ?)"
            n_par = 2
        where = "(" + join.join([uno] * len(t)) + ")"
        par = []
        for x in t:
            par.extend(["%%%s%%" % x] * n_par)
        sql = ("SELECT id FROM facts WHERE %s AND %s ORDER BY created_at DESC"
               % (where, BASE))
        ids = [r[0] for r in cur.execute(sql, tuple(par))]
        if ids:
            return ids
    return []


def main():
    con = apri()
    cur = con.cursor()
    tot = cur.execute("SELECT COUNT(*) FROM facts WHERE %s" % BASE).fetchone()[0]
    print("corpus servibile: %d - query = parole del TOPIC - n=%d per fascia" % (tot, N))
    print("%-8s %5s | %9s %9s %9s | %9s %9s %9s" % (
        "fascia", "n", "top5 P", "mai P", "cand. P", "top5 P+T", "mai P+T", "cand. P+T"))
    for nome, ordine, off in (
            ("recenti", "DESC", 0), ("medi", "DESC", tot // 2), ("vecchi", "ASC", 0)):
        sql = ("SELECT id, topic FROM facts WHERE %s ORDER BY created_at %s "
               "LIMIT %d OFFSET %d" % (BASE, ordine, N * 3, off))
        usati = 0
        p5 = pmai = t5 = tmai = 0
        cp, ct = [], []
        for fid, topic in cur.execute(sql).fetchall():
            if usati >= N:
                break
            parole = [w for w in re.split(r"[/\-_\s]+", (topic or "").lower()) if len(w) >= 3]
            if len(parole) < 2:
                continue
            usati += 1
            q = " ".join(parole)
            a = cerca(cur, parole, q, "p")
            b = cerca(cur, parole, q, "pt")
            cp.append(len(a)); ct.append(len(b))
            if fid in a[:5]:
                p5 += 1
            if fid not in a:
                pmai += 1
            if fid in b[:5]:
                t5 += 1
            if fid not in b:
                tmai += 1
        mp = sorted(cp)[len(cp) // 2] if cp else 0
        mt = sorted(ct)[len(ct) // 2] if ct else 0
        print("%-8s %5d | %9d %9d %9d | %9d %9d %9d" % (
            nome, usati, p5, pmai, mp, t5, tmai, mt))
    con.close()


if __name__ == "__main__":
    main()
