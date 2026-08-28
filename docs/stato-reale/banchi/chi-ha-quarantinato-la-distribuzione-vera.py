# -*- coding: utf-8 -*-
"""CONTROLLO della spiegazione: la vista scarta le etichette generiche?

client.py:2654-2657 riempie `layers` dalla colonna SOLO se il valore non e'
una delle tre etichette generiche:
    if _qb and _qb not in ("gate", "moat", "store-screen"): row["layers"] = [_qb]

Se la spiegazione regge, la somma delle righe con quelle tre etichette + quelle
con la colonna VUOTA deve dare esattamente il numero di `layers` vuoti (408).
Se non torna, la mia spiegazione e' sbagliata e lo dico.
"""
import collections
import sys

from verimem.client import Memory
from verimem.config import CONFIG

GENERICHE = ("gate", "moat", "store-screen")

m = Memory()
rows = m.quarantine_log(limit=500)
print(f"  db: {CONFIG.semantic_db}")
print(f"  righe: {len(rows)}")

dist = collections.Counter((r.get("quarantined_by") or "<VUOTA>").strip() or "<VUOTA>"
                           for r in rows)
print("\n  == distribuzione di `quarantined_by` sulle 500 righe")
for k, v in dist.most_common(15):
    marchio = "  <- SCARTATA dalla vista" if k in GENERICHE else (
        "  <- colonna vuota" if k == "<VUOTA>" else "")
    print(f"     {v:>4}  {k}{marchio}")

scartate = sum(v for k, v in dist.items() if k in GENERICHE)
vuote = dist.get("<VUOTA>", 0)
utili = sum(v for k, v in dist.items() if k not in GENERICHE and k != "<VUOTA>")
layers_vuoti = sum(1 for r in rows if not r.get("layers"))

print("\n  == LA PREDIZIONE della spiegazione")
print(f"     generiche scartate : {scartate}")
print(f"     colonna vuota      : {vuote}")
print(f"     somma attesa       : {scartate + vuote}")
print(f"     layers vuoti VERI  : {layers_vuoti}")
print(f"     etichette utili    : {utili}")

print("\n  -- CONTROLLO: la spiegazione regge?")
if scartate + vuote == layers_vuoti:
    print(f"     RETTA - {scartate} + {vuote} = {layers_vuoti}, esattamente i"
          " layers vuoti misurati.")
    print(f"     ⇒ la colonna e' piena su {utili + scartate} righe su {len(rows)},"
          f" ma la vista ne usa {utili}.")
else:
    print(f"     CADUTA - {scartate} + {vuote} = {scartate + vuote}, ma i layers"
          f" vuoti sono {layers_vuoti}.")
    print("     La mia spiegazione NON basta a rendere conto del numero.")
    sys.exit(1)
