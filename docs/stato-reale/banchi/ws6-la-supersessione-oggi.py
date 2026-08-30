"""Ri-misura il righello del fatto cb4043575870: le coppie (ritirato,
sostituto) e la loro similarita' di Jaccard, PIU' il controllo che dice se un
eventuale miglioramento sia reale o solo un effetto di come scriviamo.

Sotto 0.15 = "parlano d'ALTRO" (un fratello ritirato per sbaglio);
sopra 0.80 = duplicati (aggiornamento legittimo).

Il perimetro e' `writer_role='user'` — le scritture NOSTRE. Sul corpus intero
si mescolano con quelle degli automatismi (agent_inference, system_hook) e il
confronto con la misura storica salta.

SOLA LETTURA (mode=ro, solo SELECT).
"""
import datetime
import os
import random
import sqlite3
import statistics

SPARTIACQUE = "2026-08-25"          # data della cura registrata in memoria
FASCE = [(0.00, 0.15, "parlano d'ALTRO"), (0.15, 0.50, "intermedi"),
         (0.50, 0.80, "simili"), (0.80, 1.01, "duplicati")]

DB = os.path.expanduser(os.path.join("~", ".engram", "semantic", "semantic.db"))
con = sqlite3.connect("file:%s?mode=ro" % DB.replace(os.sep, "/"), uri=True)
c = con.cursor()
print("istante: %s"
      % c.execute("SELECT datetime('now','localtime')").fetchone()[0])


def tok(s):
    return {w.strip(".,;:()[]\"'").lower() for w in str(s or "").split()
            if len(w) > 2}


def jac(a, b):
    return None if (not a or not b) else len(a & b) / float(len(a | b))


def giorno(v):
    try:
        return datetime.datetime.fromtimestamp(float(v)).strftime("%Y-%m-%d")
    except Exception:
        return "?"


# ---------------------------------------------------------------- supersessioni
coppie = []
for rp, rt, sat, st, sp, stp in c.execute(
        "SELECT r.proposition, r.topic, r.superseded_at, r.status, "
        "       s.proposition, s.topic "
        "FROM facts r JOIN facts s ON s.id = r.superseded_by "
        "WHERE r.superseded_by IS NOT NULL AND r.writer_role = 'user'"):
    if str(st or "") == "quarantined":
        continue
    j = jac(tok(rp), tok(sp))
    if j is not None:
        coppie.append((j, giorno(sat), rt == stp))


def stampa(sub, eti):
    if not sub:
        print("\n== %s: nessuna coppia ==" % eti)
        return
    print("\n== %s: %d coppie ==" % (eti, len(sub)))
    for a, z, nome in FASCE:
        v = [x for x in sub if a <= x[0] < z]
        if not v:
            print("   %-18s    0 ( 0.0%%)" % nome)
            continue
        print("   %-18s %4d (%4.1f%%)   stesso topic %5.1f%%"
              % (nome, len(v), 100.0 * len(v) / len(sub),
                 100.0 * sum(1 for x in v if x[2]) / len(v)))
    print("   mediana jaccard %.3f" % statistics.median([x[0] for x in sub]))


stampa(coppie, "SCRITTE DA NOI — tutte")
stampa([x for x in coppie if x[1] < SPARTIACQUE], "DA NOI, prima del 25/08")
stampa([x for x in coppie if x[1] >= SPARTIACQUE], "DA NOI, dal 25/08")

# ------------------------------------------------------------------- controllo
# Se scrivessimo fatti piu' simili fra loro, il jaccard salirebbe da solo e il
# miglioramento sarebbe un'illusione contabile. Il fondo lo dice.
print("\n== CONTROLLO: somiglianza di fondo fra fatti NOSTRI vivi dello "
      "stesso topic, mai coinvolti in supersessione ==")
per = {"prima": [], "dopo": []}
for p, t, ca in c.execute(
        "SELECT proposition, topic, created_at FROM facts "
        "WHERE writer_role = 'user' AND superseded_by IS NULL "
        "AND proposition IS NOT NULL"):
    g = giorno(ca)
    if g < "2026-07-01":
        continue
    per["prima" if g < SPARTIACQUE else "dopo"].append((str(t or ""), tok(p)))

random.seed(7)
for k in ("prima", "dopo"):
    bytopic = {}
    for t, s in per[k]:
        bytopic.setdefault(t, []).append(s)
    campione = []
    for ss in bytopic.values():
        if len(ss) < 2:
            continue
        for _ in range(min(40, len(ss))):
            a, b = random.sample(ss, 2)
            j = jac(a, b)
            if j is not None:
                campione.append(j)
    if not campione:
        print("   %-6s nessuna coppia" % k)
        continue
    sotto = sum(1 for j in campione if j < 0.15)
    print("   %-6s fatti %5d  coppie campionate %5d  mediana %.3f  "
          "sotto 0.15: %.1f%%"
          % (k, len(per[k]), len(campione), statistics.median(campione),
             100.0 * sotto / len(campione)))
print("\n   Il fondo e' la quota che colpirebbe un ritiro CIECO dentro il "
      "topic:\n   confrontala con la fascia \"parlano d'ALTRO\" qui sopra.")
con.close()
