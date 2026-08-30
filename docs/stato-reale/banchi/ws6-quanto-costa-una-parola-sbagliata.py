"""Quanto costa UNA parola sbagliata?

A variabile singola: stessa query (le prime 8 parole del fatto), una volta
esatta e una volta con UNA parola in piu' che nel fatto NON c'e'. La parola
aggiunta fa crollare il ramo AND a zero: scatta il ripiego OR, e li' si
misura il seppellimento per data.

Stratificato per eta'. Sola lettura: mode=ro, solo SELECT.
"""
import sqlite3

from verimem.bm25_rank import _tokens as informativi
from verimem.config import CONFIG

BASE = ("status NOT IN ('orphaned','quarantined','user_belief') "
        "AND superseded_by IS NULL AND status != 'legacy_unverified'")
N = 20
PAROLE = 8
# parole comuni del nostro gergo: la prima assente dal fatto viene aggiunta
INTRUSE = ["grounding", "layer", "fonte", "claim", "gate", "gioved"]


def apri():
    p = str(CONFIG.semantic_db).replace("\\", "/")
    return sqlite3.connect("file:%s?mode=ro" % p, uri=True)


def cerca(cur, toks_and, q_completa):
    """Replica la porta: AND su tutti i token, se zero ripiego OR."""
    for ramo in ("AND", "OR"):
        toks = toks_and if ramo == "AND" else (
            [t for t in informativi(q_completa) if len(t) >= 2] or toks_and)
        join = " AND " if ramo == "AND" else " OR "
        if len(toks) == 1:
            where = "LOWER(proposition) LIKE ?"
        else:
            where = "(" + join.join(["LOWER(proposition) LIKE ?"] * len(toks)) + ")"
        sql = "SELECT id FROM facts WHERE %s AND %s ORDER BY created_at DESC" % (where, BASE)
        ids = [r[0] for r in cur.execute(sql, tuple("%%%s%%" % t for t in toks))]
        if ids:
            return ids, ramo
    return [], "zero"


def main():
    con = apri()
    cur = con.cursor()
    tot = cur.execute("SELECT COUNT(*) FROM facts WHERE %s" % BASE).fetchone()[0]
    print("corpus servibile: %d fatti · aggiungo UNA parola assente dal fatto" % tot)
    print("%-8s %6s %7s %7s %9s %9s" % (
        "fascia", "n", "top5-ok", "top5-KO", "pos.med", "candidati"))
    for nome, ordine, off in (
            ("recenti", "DESC", 0), ("medi", "DESC", tot // 2), ("vecchi", "ASC", 0)):
        sql = ("SELECT id, proposition FROM facts WHERE %s ORDER BY created_at %s "
               "LIMIT %d OFFSET %d" % (BASE, ordine, N, off))
        ok = ko = 0
        pos_ko, cand_ko = [], []
        for fid, prop in cur.execute(sql).fetchall():
            testo = (prop or "").lower()
            q = " ".join((prop or "").split()[:PAROLE])
            toks = [t for t in q.lower().split() if len(t) >= 2]
            if not toks:
                continue
            intrusa = next((w for w in INTRUSE if w not in testo), None)
            if intrusa is None:
                continue
            ids_a, _ = cerca(cur, toks, q)
            if fid in ids_a[:5]:
                ok += 1
            q2 = q + " " + intrusa
            ids_b, _r = cerca(cur, toks + [intrusa], q2)
            if fid in ids_b[:5]:
                ko += 1
            pos_ko.append(ids_b.index(fid) if fid in ids_b else -1)
            cand_ko.append(len(ids_b))
        vis = [p for p in pos_ko if p >= 0]
        med = sorted(vis)[len(vis) // 2] if vis else -1
        medc = sorted(cand_ko)[len(cand_ko) // 2] if cand_ko else 0
        print("%-8s %6d %7d %7d %9d %9d" % (nome, len(cand_ko), ok, ko, med, medc))
    con.close()


if __name__ == "__main__":
    main()
