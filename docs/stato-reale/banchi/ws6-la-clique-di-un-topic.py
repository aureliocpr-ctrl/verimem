"""Da dove vengono le 93.263 contraddizioni irrisolte?

Risposta misurata: da pochissimi topic, e dentro quei topic il rilevatore
dichiara in conflitto quasi TUTTE le coppie possibili. In piu' il registro
contiene righe duplicate.

SOLA LETTURA (mode=ro, solo SELECT).
"""
import os
import sqlite3

DB = os.path.expanduser(os.path.join("~", ".engram", "semantic", "semantic.db"))
con = sqlite3.connect("file:%s?mode=ro" % DB.replace(os.sep, "/"), uri=True)
c = con.cursor()
print("istante: %s"
      % c.execute("SELECT datetime('now','localtime')").fetchone()[0])

tot = c.execute("SELECT COUNT(*) FROM contradictions "
                "WHERE resolved_at IS NULL").fetchone()[0]
DISTINTE = (
    "SELECT COUNT(*) FROM (SELECT DISTINCT "
    " CASE WHEN fact_a_id < fact_b_id THEN fact_a_id ELSE fact_b_id END AS p,"
    " CASE WHEN fact_a_id < fact_b_id THEN fact_b_id ELSE fact_a_id END AS q"
    " FROM contradictions WHERE resolved_at IS NULL)")
dist = c.execute(DISTINTE).fetchone()[0]
print("\nrighe irrisolte              : %6d" % tot)
print("coppie non ordinate distinte : %6d" % dist)
print("  => %d righe in eccesso (%.0f%%): la stessa coppia registrata piu' volte"
      % (tot - dist, 100.0 * (tot - dist) / max(1, tot)))

div = c.execute(
    "SELECT COUNT(*) FROM contradictions x "
    "JOIN facts a ON a.id = x.fact_a_id JOIN facts b ON b.id = x.fact_b_id "
    "WHERE x.resolved_at IS NULL AND a.topic <> b.topic").fetchone()[0]
print("\ncoppie fra topic DIVERSI: %d = %.1f%%   "
      "(il rilevatore confronta solo dentro il topic)"
      % (div, 100.0 * div / max(1, tot)))

print("\n== i topic che generano piu' coppie ==")
righe = c.execute(
    "SELECT a.topic, COUNT(*) FROM contradictions x "
    "JOIN facts a ON a.id = x.fact_a_id JOIN facts b ON b.id = x.fact_b_id "
    "WHERE x.resolved_at IS NULL AND a.topic = b.topic "
    "GROUP BY a.topic ORDER BY COUNT(*) DESC LIMIT 6").fetchall()
cum = 0
for t, q in righe:
    cum += q
    print("   %-44s %6d = %4.1f%%   (cumulato %4.1f%%)"
          % (str(t)[:44] or "(topic vuoto)", q, 100.0 * q / tot,
             100.0 * cum / tot))

print("\n== la clique: quante delle coppie POSSIBILI sono dichiarate in conflitto ==")
for t, _ in righe[:3]:
    if t is None:
        continue
    n = c.execute("SELECT COUNT(*) FROM facts WHERE topic = ?", (t,)).fetchone()[0]
    poss = n * (n - 1) // 2
    d = c.execute(
        "SELECT COUNT(*) FROM (SELECT DISTINCT "
        " CASE WHEN x.fact_a_id < x.fact_b_id THEN x.fact_a_id ELSE x.fact_b_id END AS p,"
        " CASE WHEN x.fact_a_id < x.fact_b_id THEN x.fact_b_id ELSE x.fact_a_id END AS q"
        " FROM contradictions x JOIN facts a ON a.id = x.fact_a_id "
        " JOIN facts b ON b.id = x.fact_b_id "
        " WHERE x.resolved_at IS NULL AND a.topic = ? AND b.topic = ?)",
        (t, t)).fetchone()[0]
    print("   %-44s %4d fatti, %6d coppie possibili, %6d dichiarate = %5.1f%%"
          % (str(t)[:44], n, poss, d, 100.0 * d / max(1, poss)))
print("   (i fatti sono contati senza escludere i superati: il denominatore e'"
      "\n    un'approssimazione per eccesso)")
con.close()
