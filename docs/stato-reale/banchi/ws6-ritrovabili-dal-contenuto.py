"""Chiude il limite del doc 51: i miei fatti si ritrovano cercandone il
CONTENUTO invece del nome del topic?

Tre righelli, dal piu' onesto al piu' facile:
  A  query = il TOPIC in parole                (gia' misurato: 8,6%)
  B  query = un FRAMMENTO della proposizione   (chi ricorda un pezzo di frase)
  C  query = la proposizione INTERA            (il caso facile, per il tetto)

Il confronto fra i tre dice se il problema sia il retrieval o la chiave.
Store di Aurelio: SOLA LETTURA (la recall e' una lettura).
"""
import os
import sqlite3
import sys

DB = os.path.expanduser(os.path.join("~", ".engram", "semantic", "semantic.db"))
K = 10
ELENCO = sys.argv[1]

miei = {r.strip() for r in open(ELENCO, encoding="utf-8") if r.strip()}
con = sqlite3.connect("file:{}?mode=ro".format(DB.replace(os.sep, "/")), uri=True)
c = con.cursor()
ph = ",".join("?" * len(miei))
righe = c.execute(f"SELECT id, topic, proposition FROM facts WHERE id IN ({ph}) "
                  "AND superseded_by IS NULL", tuple(miei)).fetchall()
con.close()
print("miei fatti VIVI da cercare: %d" % len(righe))

from verimem.client import Memory  # noqa: E402

m = Memory(DB)


def cerca(q, atteso):
    try:
        res = m.recall(q, k=K)
    except Exception:
        return False, False
    degradato = False
    for it in (res or []):
        if isinstance(it, dict):
            if str(it.get("ranking") or "") == "keyword":
                degradato = True
            if it.get("id") == atteso:
                return True, degradato
        elif getattr(it, "id", None) == atteso:
            return True, degradato
    return False, degradato


def frammento(p, n=7):
    return " ".join(str(p).split()[:n])


esiti = {"A": [0, 0], "B": [0, 0], "C": [0, 0]}
degradate = 0
for fid, topic, prop in righe:
    for etichetta, q in (
            ("A", str(topic).split("/", 1)[-1].replace("-", " ")),
            ("B", frammento(prop)),
            ("C", str(prop)[:180])):
        ok, deg = cerca(q, fid)
        esiti[etichetta][1] += 1
        if ok:
            esiti[etichetta][0] += 1
        if deg:
            degradate += 1

print("\n%-3s %-34s %10s" % ("", "query costruita da…", "ritrovati"))
for k, testo in (("A", "il TOPIC in parole"),
                 ("B", "un FRAMMENTO (7 parole) della frase"),
                 ("C", "la proposizione INTERA (caso facile)")):
    trov, tot = esiti[k]
    print("%-3s %-34s %5d/%-3d = %5.1f%%"
          % (k, testo, trov, tot, 100.0 * trov / max(1, tot)))
print("\ncorse degradate: %d su %d" % (degradate, 3 * len(righe)))
