"""La query NON viene dal topic del fatto cercato: chiude la circolarita'.

Tutte le misure precedenti usavano le parole del topic come domanda,
quindi cercare nel topic trovava per costruzione. Qui la domanda sono le
prime otto parole della proposition di un ALTRO fatto che condivide il
prefisso di topic con quello cercato: e' il caso vero di chi ricorda
l'argomento e cerca con parole sue.

Predizione dichiarata prima: cosi' il campo topic non aiuta, perche' le
parole della prosa non compaiono nei topic.

Sola lettura: mode=ro, solo SELECT.
"""
import sqlite3

from verimem.bm25_rank import _tokens as informativi
from verimem.config import CONFIG

BASE = ("status NOT IN ('orphaned','quarantined','user_belief') "
        "AND superseded_by IS NULL AND status != 'legacy_unverified'")
N = 20
PAROLE = 8


def apri():
    p = str(CONFIG.semantic_db).replace("\\", "/")
    return sqlite3.connect("file:%s?mode=ro" % p, uri=True)


def cerca(cur, toks, q, campi):
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
            return ids
    return []


def fratello(cur, fid, topic):
    """Un altro fatto con lo stesso prefisso di topic."""
    pre = "/".join((topic or "").split("/")[:2])
    if not pre:
        return None
    r = cur.execute(
        "SELECT proposition FROM facts WHERE %s AND topic LIKE ? AND id != ? LIMIT 1" % BASE,
        (pre + "%", fid)).fetchone()
    return r[0] if r else None


def main():
    con = apri()
    cur = con.cursor()
    tot = cur.execute("SELECT COUNT(*) FROM facts WHERE %s" % BASE).fetchone()[0]
    print("corpus servibile: %d - query = prosa di un FRATELLO, non il topic" % tot)
    print("%-8s %5s | %7s %7s %8s | %9s %9s %8s" % (
        "fascia", "n", "top5 P", "mai P", "cand. P", "top5 P+T", "mai P+T", "cand.P+T"))
    for nome, ordine, off in (
            ("recenti", "DESC", 0), ("medi", "DESC", tot // 2), ("vecchi", "ASC", 0)):
        sql = ("SELECT id, topic FROM facts WHERE %s ORDER BY created_at %s "
               "LIMIT %d OFFSET %d" % (BASE, ordine, N * 4, off))
        usati = p5 = pmai = t5 = tmai = 0
        cp, ct = [], []
        for fid, topic in cur.execute(sql).fetchall():
            if usati >= N:
                break
            testo = fratello(cur, fid, topic)
            if not testo:
                continue
            q = " ".join(testo.split()[:PAROLE])
            toks = [w for w in q.lower().split() if len(w) >= 3]
            if len(toks) < 2:
                continue
            usati += 1
            a = cerca(cur, toks, q, "p")
            b = cerca(cur, toks, q, "pt")
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
        print("%-8s %5d | %7d %7d %8d | %9d %9d %8d" % (
            nome, usati, p5, pmai, mp, t5, tmai, mt))
    con.close()


if __name__ == "__main__":
    main()
