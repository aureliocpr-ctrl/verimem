"""Sotto le contraddizioni irrisolte, quelle in cui i due fatti parlano DAVVERO
della stessa cosa (jaccard alto): che cosa sono?

Risposta misurata: quasi tutte differiscono per pochissimi token, e quei token
sono timestamp, contatori, orari. Sono la stessa riga di LOG a istanti diversi,
non contraddizioni.

SOLA LETTURA (mode=ro, solo SELECT). Nessuna correzione: solo lettura.
"""
import collections
import os
import sqlite3

SOGLIA = 0.50
DB = os.path.expanduser(os.path.join("~", ".engram", "semantic", "semantic.db"))
con = sqlite3.connect("file:%s?mode=ro" % DB.replace(os.sep, "/"), uri=True)
c = con.cursor()
print("istante: %s"
      % c.execute("SELECT datetime('now','localtime')").fetchone()[0])


def tok(s):
    return {w.strip(".,;:()[]\"'").lower() for w in str(s or "").split()
            if len(w) > 1}


dist = collections.Counter()
esempi = {}
alte = []
test = 0
for pa, pb, ta, tb, sa, sb in c.execute(
        "SELECT a.proposition, b.proposition, a.topic, b.topic, "
        "       a.status, b.status FROM contradictions x "
        "JOIN facts a ON a.id = x.fact_a_id JOIN facts b ON b.id = x.fact_b_id "
        "WHERE x.resolved_at IS NULL"):
    A, B = tok(pa), tok(pb)
    if not A or not B:
        continue
    if len(A & B) / float(len(A | B)) < SOGLIA:
        continue
    if str(ta or "").startswith("test/") or str(tb or "").startswith("test/"):
        test += 1
        continue
    k = len(A ^ B)                       # token esclusivi, la differenza intera
    dist[k] += 1
    alte.append((k, pa, pb, ta, sa, sb))
    if k not in esempi and k <= 4:
        esempi[k] = (sorted(A - B)[:4], sorted(B - A)[:4], str(pa)[:96])

n = sum(dist.values())
print("\ncoppie irrisolte con jaccard >= %.2f:" % SOGLIA)
print("   con un topic test/... : %5d  (escluse dal resto)" % test)
print("   non-test              : %5d" % n)

print("\n== quanti TOKEN ESCLUSIVI separano le due frasi ==")
cum = 0
for k in sorted(dist):
    cum += dist[k]
    if k <= 12:
        print("   %2d token -> %5d coppie   (cumulato %5d = %5.1f%%)"
              % (k, dist[k], cum, 100.0 * cum / n))
pochi = sum(v for k, v in dist.items() if k <= 4)
print("\n   >>> differiscono per AL PIU' 4 TOKEN: %d = %.1f%%"
      % (pochi, 100.0 * pochi / max(1, n)))

print("\n== e quei token cosa sono ==")
for k in sorted(esempi):
    a, b, frase = esempi[k]
    print("   %d token: solo-A=%s   solo-B=%s" % (k, a, b))
    print("      \"%s\"" % frase)

print("\n== le coppie con PIU' token di differenza: i candidati da leggere ==")
alte.sort(reverse=True)
for k, pa, pb, ta, sa, sb in alte[:6]:
    print("\n--- %d token di differenza   topic=%s" % (k, str(ta)[:50]))
    print("    A [%s] %s" % (sa, str(pa)[:130]))
    print("    B [%s] %s" % (sb, str(pb)[:130]))
con.close()
