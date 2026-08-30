"""Perche' un FRAMMENTO di 7 parole ritrova meglio della frase INTERA?

Banco della ritrovabilita': A(topic)=12,1%  B(7 parole)=100%  C(intera)=95,5%.
C dovrebbe essere il caso piu' facile e invece perde. Ipotesi da falsificare:
esiste una lunghezza di query oltre la quale il recall PEGGIORA.

Righello: stesso fatto, stessa attesa, solo la lunghezza della query cambia.
Store di Aurelio: SOLA LETTURA (recall).
"""
import os
import sqlite3
import sys

DB = os.path.expanduser(os.path.join("~", ".engram", "semantic", "semantic.db"))
K = 10
LUNGHEZZE = [3, 5, 7, 10, 15, 20, 30]
ELENCO = sys.argv[1]

miei = {r.strip() for r in open(ELENCO, encoding="utf-8") if r.strip()}
con = sqlite3.connect("file:{}?mode=ro".format(DB.replace(os.sep, "/")), uri=True)
ph = ",".join("?" * len(miei))
righe = con.execute(
    f"SELECT id, proposition FROM facts WHERE id IN ({ph}) "
    "AND superseded_by IS NULL", tuple(miei)).fetchall()
con.close()
righe = [(i, p) for i, p in righe if len(str(p).split()) >= 20][:40]
print("fatti usati (almeno 20 parole): %d" % len(righe))

from verimem.client import Memory  # noqa: E402 - dopo la lettura in sola lettura

m = Memory(DB)


def trova(q, atteso):
    """Ritorna (trovato, rango, punteggio_del_primo)."""
    try:
        res = m.recall(q, k=K)
    except Exception:
        return False, None, None
    primo = None
    for r, it in enumerate(res or [], 1):
        s = it.get("score") if isinstance(it, dict) else None
        if r == 1 and s is not None:
            primo = float(s)
        ident = it.get("id") if isinstance(it, dict) else getattr(it, "id", None)
        if ident == atteso:
            return True, r, primo
    return False, None, primo


print("\n%-9s %-9s %-9s %s" % ("parole", "trovati", "rango~1", "punteggio medio"))
for n in LUNGHEZZE:
    trovati = ranghi = 0
    punteggi = []
    primi = 0
    for fid, prop in righe:
        parole = str(prop).split()
        if len(parole) < n:
            continue
        ok, rango, s = trova(" ".join(parole[:n]), fid)
        ranghi += 1
        if ok:
            trovati += 1
            if rango == 1:
                primi += 1
        if s is not None:
            punteggi.append(s)
    media = sum(punteggi) / len(punteggi) if punteggi else float("nan")
    print("%-9d %2d/%-6d %2d/%-6d %.4f"
          % (n, trovati, ranghi, primi, ranghi, media))

print("\nprima parola di riferimento: frase intera")
trovati = primi = tot = 0
punteggi = []
for fid, prop in righe:
    ok, rango, s = trova(str(prop), fid)
    tot += 1
    if ok:
        trovati += 1
        if rango == 1:
            primi += 1
    if s is not None:
        punteggi.append(s)
media = sum(punteggi) / len(punteggi) if punteggi else float("nan")
print("%-9s %2d/%-6d %2d/%-6d %.4f"
      % ("intera", trovati, tot, primi, tot, media))
