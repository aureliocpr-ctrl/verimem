"""Quanti fatti non sono MAI passati dal moat, e quando sono entrati.
`grounding_score IS NULL` = mai giudicato (non "giudicato male").
SOLA LETTURA: mode=ro, solo SELECT."""
import os
import sqlite3
import collections
import datetime

DB = os.path.expanduser(os.path.join("~", ".engram", "semantic", "semantic.db"))
con = sqlite3.connect("file:%s?mode=ro" % DB.replace(os.sep, "/"), uri=True)
c = con.cursor()

ist = c.execute("SELECT datetime('now','localtime')").fetchone()[0]
tot = c.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
mai = c.execute(
    "SELECT COUNT(*) FROM facts WHERE grounding_score IS NULL").fetchone()[0]
print("istante della misura: %s" % ist)
print("fatti: %d   mai giudicati (grounding_score IS NULL): %d = %.1f%%"
      % (tot, mai, 100.0 * mai / max(1, tot)))


def giorno(ca):
    try:
        return datetime.datetime.fromtimestamp(float(ca)).strftime("%Y-%m-%d")
    except Exception:
        return str(ca)[:10]


tot_g = collections.Counter()
mai_g = collections.Counter()
for ca, gs in c.execute("SELECT created_at, grounding_score FROM facts"):
    g = giorno(ca)
    tot_g[g] += 1
    if gs is None:
        mai_g[g] += 1

print("\n== per giorno (ultimi 16 con almeno un fatto) ==")
print("%-12s %8s %8s %8s" % ("giorno", "fatti", "mai giud.", "%"))
for g in sorted(tot_g)[-16:]:
    t = tot_g[g]
    m = mai_g[g]
    print("%-12s %8d %8d %7.1f%%" % (g, t, m, 100.0 * m / max(1, t)))

print("\n== i giorni PEGGIORI di sempre (>=20 fatti) ==")
peggio = [(100.0 * mai_g[g] / tot_g[g], g, tot_g[g], mai_g[g])
          for g in tot_g if tot_g[g] >= 20]
peggio.sort(reverse=True)
for pc, g, t, m in peggio[:8]:
    print("   %-12s %5d fatti, %5d mai giudicati = %5.1f%%" % (g, t, m, pc))

print("\n== e i topic piu' colpiti fra i mai giudicati ==")
for t, n in c.execute(
        "SELECT COALESCE(topic,'(nessuno)'), COUNT(*) FROM facts "
        "WHERE grounding_score IS NULL GROUP BY topic "
        "ORDER BY COUNT(*) DESC LIMIT 8"):
    print("   %-44s %5d" % (t[:44], n))
con.close()
