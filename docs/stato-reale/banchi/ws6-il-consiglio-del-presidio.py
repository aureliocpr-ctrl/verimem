"""`verimem doctor` avverte che i fatti senza trust rank «are NEVER auto-retired
in a contradiction, so those clashes pile up unresolved» e consiglia di
normalizzare quegli status.

Questo banco misura cosa costerebbe seguirlo:
  1. quante contraddizioni ci sono e quante sono irrisolte
  2. quante coinvolgono un fatto senza trust rank, e quanti fatti DISTINTI
     (il numero che conta: un fatto compare in molte coppie)
  3. se quelle contraddizioni siano vere, col righello Jaccard del doc 41

SOLA LETTURA (mode=ro, solo SELECT).
"""
import os
import random
import sqlite3
import statistics

SENZA_RANK = ("user_manual", "bootstrap_rule", "bootstrap_lesson", "diary")
CAMPIONE = 4000

DB = os.path.expanduser(os.path.join("~", ".engram", "semantic", "semantic.db"))
con = sqlite3.connect("file:%s?mode=ro" % DB.replace(os.sep, "/"), uri=True)
c = con.cursor()
ph = ",".join("?" * len(SENZA_RANK))
print("istante: %s"
      % c.execute("SELECT datetime('now','localtime')").fetchone()[0])


def tok(s):
    return {w.strip(".,;:()[]\"'").lower() for w in str(s or "").split()
            if len(w) > 2}


def jac(a, b):
    A, B = tok(a), tok(b)
    return None if (not A or not B) else len(A & B) / float(len(A | B))


# ------------------------------------------------------------------ 1. quante
tot = c.execute("SELECT COUNT(*) FROM contradictions").fetchone()[0]
irr = c.execute("SELECT COUNT(*) FROM contradictions "
                "WHERE resolved_at IS NULL").fetchone()[0]
print("\ncontraddizioni registrate: %d   irrisolte: %d (%.1f%%)"
      % (tot, irr, 100.0 * irr / max(1, tot)))
for k, n in c.execute(
        "SELECT COALESCE(kind,'(nullo)'), COUNT(*) FROM contradictions "
        "WHERE resolved_at IS NULL GROUP BY 1 ORDER BY 2 DESC"):
    print("   %-24s %6d" % (k, n))

# ------------------------------------------------- 2. il perimetro del consiglio
q = ("SELECT COUNT(*) FROM contradictions x "
     "JOIN facts a ON a.id = x.fact_a_id JOIN facts b ON b.id = x.fact_b_id "
     "WHERE x.resolved_at IS NULL AND (%s)")
coppie = c.execute(q % ("a.status IN (%s) OR b.status IN (%s)" % (ph, ph)),
                   SENZA_RANK * 2).fetchone()[0]
distinti = c.execute(
    "SELECT COUNT(DISTINCT id) FROM ("
    " SELECT x.fact_a_id AS id FROM contradictions x "
    "  JOIN facts a ON a.id = x.fact_a_id "
    "  WHERE x.resolved_at IS NULL AND a.status IN (%s)"
    " UNION SELECT x.fact_b_id FROM contradictions x "
    "  JOIN facts b ON b.id = x.fact_b_id "
    "  WHERE x.resolved_at IS NULL AND b.status IN (%s))" % (ph, ph),
    SENZA_RANK * 2).fetchone()[0]
vivi = c.execute("SELECT COUNT(*) FROM facts "
                 "WHERE superseded_by IS NULL").fetchone()[0]
senza = c.execute("SELECT COUNT(*) FROM facts WHERE superseded_by IS NULL "
                  "AND status IN (%s)" % ph, SENZA_RANK).fetchone()[0]
tutti_d = c.execute(
    "SELECT COUNT(DISTINCT id) FROM ("
    " SELECT fact_a_id AS id FROM contradictions WHERE resolved_at IS NULL"
    " UNION SELECT fact_b_id FROM contradictions WHERE resolved_at IS NULL)"
).fetchone()[0]
print("\n== il perimetro del consiglio ==")
print("   coppie irrisolte con almeno un fatto senza trust rank: %6d" % coppie)
print("   ma i fatti DISTINTI sono                             : %6d" % distinti)
print("   fatti vivi %d, di cui senza trust rank %d" % (vivi, senza))
print("   >>> normalizzare gli status renderebbe ritirabili fino a %d fatti"
      " (%.1f%% dei protetti)" % (distinti, 100.0 * distinti / max(1, senza)))
print("   fatti distinti in QUALSIASI contraddizione irrisolta: %d = %.1f%% dei vivi"
      % (tutti_d, 100.0 * tutti_d / max(1, vivi)))

# ------------------------------------------------------- 3. sono contraddizioni?
print("\n== sono contraddizioni? righello Jaccard, campione di %d coppie ==" % CAMPIONE)
rows = c.execute(
    "SELECT x.kind, a.proposition, b.proposition, a.topic, b.topic "
    "FROM contradictions x "
    "JOIN facts a ON a.id = x.fact_a_id JOIN facts b ON b.id = x.fact_b_id "
    "WHERE x.resolved_at IS NULL ORDER BY x.id LIMIT ?", (CAMPIONE,)).fetchall()
for kind in ("numeric_clash", "boolean_clash"):
    v = [(jac(a, b), ta == tb) for k, a, b, ta, tb in rows if k == kind]
    v = [(j, t) for j, t in v if j is not None]
    if not v:
        continue
    basso = sum(1 for j, _ in v if j < 0.15)
    alto = sum(1 for j, _ in v if j >= 0.50)
    print("   %-15s %5d coppie   parlano d'ALTRO (<0.15) %5d = %5.1f%%   "
          "stessa cosa (>=0.50) %4d = %4.1f%%   mediana %.3f"
          % (kind, len(v), basso, 100.0 * basso / len(v), alto,
             100.0 * alto / len(v),
             statistics.median([j for j, _ in v])))

print("\n== un campione da leggere a occhio ==")
random.seed(11)
for k, a, b, ta, tb in random.sample(rows, min(4, len(rows))):
    print("   --- kind=%s  jaccard=%.3f" % (k, jac(a, b) or 0.0))
    print("       A: %s" % str(a)[:86])
    print("       B: %s" % str(b)[:86])
con.close()
