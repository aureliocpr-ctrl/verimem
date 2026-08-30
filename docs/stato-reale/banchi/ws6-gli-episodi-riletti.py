"""Gli episodi vengono mai riletti? E la salience che il prodotto calcola su di
loro ha un consumatore?

`access_count` e' incrementato da `_bump_access_tracking` (verimem/memory.py),
chiamato da `recall()`: conta le recall vere, non i passaggi del consolidamento.
Misura pero' "servito", non "usato": sale anche se chi ha chiesto poi ignora
il risultato.

SOLA LETTURA (mode=ro, solo SELECT). NESSUN decay_run: e' una scrittura
persistente e non e' compito di un banco.
"""
import collections
import datetime
import os
import sqlite3

DB = os.path.expanduser(os.path.join("~", ".engram", "episodes", "episodes.db"))
con = sqlite3.connect("file:%s?mode=ro" % DB.replace(os.sep, "/"), uri=True)
c = con.cursor()
print("istante: %s"
      % c.execute("SELECT datetime('now','localtime')").fetchone()[0])

n = c.execute("SELECT COUNT(*) FROM episodes").fetchone()[0]
inv = c.execute("SELECT COUNT(*) FROM episodes "
                "WHERE invalidated_at IS NOT NULL").fetchone()[0]
pin = c.execute("SELECT COUNT(*) FROM episodes "
                "WHERE COALESCE(pinned,0)=1").fetchone()[0]
print("\nepisodi %d   invalidati %d   pinned %d" % (n, inv, pin))

print("\n== quante volte sono stati RILETTI ==")
d = collections.Counter()
for (a,) in c.execute("SELECT COALESCE(access_count,0) FROM episodes"):
    d[int(a)] += 1
cum = 0
for k in sorted(d):
    cum += d[k]
    if k <= 6:
        print("   %2d accessi -> %4d episodi   (cumulato %4d = %5.1f%%)"
              % (k, d[k], cum, 100.0 * cum / n))
print("   >>> MAI riletti: %d = %.1f%%" % (d.get(0, 0), 100.0 * d.get(0, 0) / n))


def per_mese(col, where="1=1"):
    g = collections.Counter()
    for (t,) in c.execute("SELECT %s FROM episodes WHERE %s AND %s IS NOT NULL"
                          % (col, where, col)):
        try:
            g[datetime.datetime.fromtimestamp(float(t)).strftime("%Y-%m")] += 1
        except Exception:
            g[str(t)[:7]] += 1
    return g


print("\n== creati / ultimo accesso, per mese ==")
crea = per_mese("created_at")
acc = per_mese("last_accessed_at", "COALESCE(access_count,0)>0")
print("%-9s %8s %8s" % ("mese", "creati", "letti"))
for k in sorted(set(crea) | set(acc)):
    print("%-9s %8d %8d" % (k, crea.get(k, 0), acc.get(k, 0)))

print("\n== la salience discrimina? (alimenta la retention, Ebbinghaus) ==")
for eti, w in (("mai serviti", "COALESCE(access_count,0)=0"),
               ("serviti", "COALESCE(access_count,0)>0")):
    r = c.execute("SELECT COUNT(*), AVG(salience_score) FROM episodes "
                  "WHERE " + w).fetchone()
    av = "%.3f" % r[1] if r[1] is not None else "n/d"
    print("   %-14s n=%4d   salience media %s" % (eti, r[0], av))
nulle = c.execute("SELECT COUNT(*) FROM episodes "
                  "WHERE salience_score IS NULL").fetchone()[0]
print("   episodi senza salience: %d" % nulle)
print("\n   >>> la salience e' calcolata e discrimina, ma gli invalidati sono %d:"
      "\n       l'oblio esiste come comando (decay_run) e non risulta eseguito."
      % inv)
con.close()
