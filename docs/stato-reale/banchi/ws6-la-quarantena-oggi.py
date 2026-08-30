"""Chi mette i fatti in quarantena, oggi, e con quale fondatezza.

Il punto che ne esce: i layer L4.x fermano fatti che il giudice di fondatezza
promuove a 96-99. Non e' una contraddizione fra i due: misurano cose diverse —
il grounding chiede "la source sostiene il senso?", L4.1 chiede "i numeri sono
QUELLI?".

SOLA LETTURA (mode=ro, solo SELECT). Nessun requalify, nessuna scrittura.
"""
import collections
import datetime
import os
import sqlite3

DB = os.path.expanduser(os.path.join("~", ".engram", "semantic", "semantic.db"))
con = sqlite3.connect("file:%s?mode=ro" % DB.replace(os.sep, "/"), uri=True)
c = con.cursor()
print("istante: %s"
      % c.execute("SELECT datetime('now','localtime')").fetchone()[0])

tot = c.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
q = c.execute("SELECT COUNT(*) FROM facts "
              "WHERE status='quarantined'").fetchone()[0]
print("\nfatti %d   quarantined %d = %.1f%%" % (tot, q, 100.0 * q / tot))

print("\n== chi li ha fermati, e con quale fondatezza ==")
print("%-24s %6s %8s %10s" % ("quarantined_by", "n", "quota", "grounding~"))
for k, n, gm, alti in c.execute(
        "SELECT COALESCE(quarantined_by,'(nullo)'), COUNT(*), "
        "       AVG(grounding_score), "
        "       SUM(CASE WHEN grounding_score >= 90 THEN 1 ELSE 0 END) "
        "FROM facts WHERE status='quarantined' "
        "GROUP BY 1 ORDER BY 2 DESC LIMIT 10"):
    g = "%.1f" % gm if gm is not None else "n/d"
    print("%-24s %6d %7.1f%% %10s   con grounding>=90: %d"
          % (str(k)[:24], n, 100.0 * n / q, g, alti or 0))


def per_mese(where):
    g = collections.Counter()
    for (ca,) in c.execute("SELECT created_at FROM facts "
                           "WHERE status='quarantined' AND " + where):
        try:
            g[datetime.datetime.fromtimestamp(float(ca)).strftime("%Y-%m")] += 1
        except Exception:
            g[str(ca)[:7]] += 1
    return g


print("\n== quando: il campo quarantined_by e' nato ad agosto ==")
a = per_mese("quarantined_by IS NULL")
b = per_mese("quarantined_by IS NOT NULL")
print("%-9s %10s %10s" % ("mese", "senza", "con"))
for k in sorted(set(a) | set(b)):
    print("%-9s %10d %10d" % (k, a.get(k, 0), b.get(k, 0)))
ago_s, ago_c = a.get("2026-08", 0), b.get("2026-08", 0)
if ago_s + ago_c:
    print("   >>> anche ad agosto, %d su %d (%.1f%%) NON dichiarano chi li ha "
          "fermati" % (ago_s, ago_s + ago_c, 100.0 * ago_s / (ago_s + ago_c)))

print("\n== i casi che contano: fermati da un layer NONOSTANTE grounding alto ==")
print("   (claim e source affiancati: giudicali tu, il banco non decide)")
for p, gs, span, t in c.execute(
        "SELECT proposition, grounding_score, grounding_span, topic "
        "FROM facts WHERE status='quarantined' AND quarantined_by='L4.1' "
        "AND grounding_score >= 95 ORDER BY grounding_score DESC LIMIT 4"):
    print("\n--- grounding %.2f  topic=%s" % (gs, str(t)[:52]))
    print("    CLAIM : %s" % str(p)[:190])
    print("    SOURCE: %s" % str(span or "(nessuna)")[:190])
con.close()
