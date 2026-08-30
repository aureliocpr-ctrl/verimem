"""Dei fatti trattenuti CON il giudice a favore, chi li ha fermati?

Incrocia due reperti che non si erano incontrati:
  - ws7 (LANT-79): il 44% dei quarantinati recenti ha grounding >= 80
  - ws6 (doc 24):  L4.1 fa il 35% delle quarantene dal 21/08, e prima 0%
  - ws7 (W7-16 firmata): L4.1 ferma a grounding 99,6, scavalcando il moat

Se i trattenuti-col-giudice-a-favore sono in maggioranza fermati da L4.1,
il 44% ha un NOME e un meccanismo, invece di essere un numero.

Store in SOLA LETTURA.
"""
import sqlite3
from collections import Counter

from verimem.config import CONFIG

con = sqlite3.connect(f"file:{CONFIG.semantic_db}?mode=ro", uri=True)
DUE_GIORNI = "created_at >= strftime('%s','now') - 172800"


def chi(dove: str) -> Counter:
    c: Counter = Counter()
    for (qb,) in con.execute(
            f"SELECT quarantined_by FROM facts WHERE status='quarantined' AND {dove}"):
        c[(qb or "(vuoto)").strip()[:40]] += 1
    return c

alti = chi(f"grounding_score >= 80 AND {DUE_GIORNI}")
bassi = chi(f"grounding_score < 80 AND {DUE_GIORNI}")
print(f"  ultimi 2 giorni — quarantinati CON il giudice a favore (>=80): {sum(alti.values())}")
for k, n in alti.most_common(8):
    print(f"      {n:4}  {k}")
print(f"\n  ultimi 2 giorni — quarantinati col giudice CONTRO (<80): {sum(bassi.values())}")
for k, n in bassi.most_common(8):
    print(f"      {n:4}  {k}")

#: la domanda che decide: L4.1 e' concentrato sui buoni o distribuito?
def quota(c: Counter, chiave: str) -> str:
    tot = sum(c.values())
    n = sum(v for k, v in c.items() if chiave.lower() in k.lower())
    return f"{n}/{tot} = {100*n/tot:.0f}%" if tot else "0/0"

print(f"\n  quota di L4.1 fra i trattenuti col GIUDICE A FAVORE: {quota(alti, 'L4.1')}")
print(f"  quota di L4.1 fra i trattenuti col giudice CONTRO:   {quota(bassi, 'L4.1')}")
print("\n  ⇒ se la prima e' molto piu' alta della seconda, L4.1 e' il meccanismo")
print("     che produce la popolazione «trattenuto ma sostenuto dal giudice».")
