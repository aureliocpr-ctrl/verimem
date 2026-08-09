import sqlite3, collections
con = sqlite3.connect("file:C:/Users/aurel/.engram/semantic/semantic.db?mode=ro", uri=True)
print("MARK === CHI li mette in quarantena? (campo quarantined_by) ===")
for r in con.execute("SELECT COALESCE(quarantined_by,'(vuoto)'), count(*) FROM facts "
                     "WHERE status='quarantined' GROUP BY 1 ORDER BY 2 DESC LIMIT 8"):
    print("MARK   " + str(r[0])[:40].ljust(42) + str(r[1]).rjust(6))
print("MARK")
print("MARK === e per i 55 con punteggio ALTO (>=90) ===")
for r in con.execute("SELECT COALESCE(quarantined_by,'(vuoto)'), count(*) FROM facts "
                     "WHERE status='quarantined' AND grounding_score>=90 GROUP BY 1 ORDER BY 2 DESC"):
    print("MARK   " + str(r[0])[:40].ljust(42) + str(r[1]).rjust(6))
print("MARK")
print("MARK === controprova simmetrica: gli AMMESSI con punteggio BASSO (<40) ===")
n = con.execute("SELECT count(*) FROM facts WHERE status='model_claim' AND grounding_score<40").fetchone()[0]
print("MARK   model_claim con gs<40: " + str(n))
for r in con.execute("SELECT id, round(grounding_score,2), substr(proposition,1,52) FROM facts "
                     "WHERE status='model_claim' AND grounding_score<40 ORDER BY grounding_score LIMIT 4"):
    print("MARK     " + r[0] + " gs=" + str(r[1]).ljust(7) + str(r[2])[:50])
con.close()
