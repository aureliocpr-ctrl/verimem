"""I fatti mai giudicati di oggi sono CONCENTRATI in finestre (morti del daemon)
o sparsi (causa diversa)?  SOLA LETTURA."""
import os
import sqlite3
import collections
import datetime

DB = os.path.expanduser(os.path.join("~", ".engram", "semantic", "semantic.db"))
con = sqlite3.connect("file:%s?mode=ro" % DB.replace(os.sep, "/"), uri=True)
c = con.cursor()

oggi = datetime.date.today()
per_ora_tot = collections.Counter()
per_ora_mai = collections.Counter()
istanti = []
for ca, gs in c.execute("SELECT created_at, grounding_score FROM facts"):
    try:
        dt = datetime.datetime.fromtimestamp(float(ca))
    except Exception:
        continue
    if dt.date() != oggi:
        continue
    k = dt.strftime("%H")
    per_ora_tot[k] += 1
    if gs is None:
        per_ora_mai[k] += 1
        istanti.append(dt)

print("== oggi, per ora: fatti scritti e mai giudicati ==")
print("%-5s %7s %10s %7s   %s" % ("ora", "fatti", "mai giud.", "%", ""))
for k in sorted(per_ora_tot):
    t = per_ora_tot[k]
    m = per_ora_mai[k]
    barra = "#" * int(round(20.0 * m / max(1, t)))
    print("%-5s %7d %10d %6.1f%%   %s" % (k + ":00", t, m, 100.0 * m / t, barra))

print("\n== i mai-giudicati di oggi: sono in blocchi contigui? ==")
istanti.sort()
if istanti:
    blocchi = []
    inizio = prec = istanti[0]
    for dt in istanti[1:]:
        if (dt - prec).total_seconds() > 600:          # 10 minuti di stacco
            blocchi.append((inizio, prec))
            inizio = dt
        prec = dt
    blocchi.append((inizio, prec))
    print("   %d fatti in %d blocchi separati da piu' di 10 minuti:"
          % (len(istanti), len(blocchi)))
    for a, z in blocchi:
        dur = (z - a).total_seconds() / 60.0
        n = sum(1 for d in istanti if a <= d <= z)
        print("     %s - %s  (%5.1f min, %3d fatti)"
              % (a.strftime("%H:%M:%S"), z.strftime("%H:%M:%S"), dur, n))
con.close()
