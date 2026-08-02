"""Dove cade la soglia? Banco costruito a mano su lingue NON coperte.

Coppie VERE  = lo stesso soggetto con un valore aggiornato (evoluzione).
Coppie FALSE = due osservazioni scorrelate (mai un'evoluzione).

Non traduco nulla a runtime: le frasi sono scritte a mano, e il verdetto
atteso e' quello di un lettore umano di quella lingua.
"""
import sys

sys.path.insert(0, r"C:\Users\aurel\Code\HippoAgent")
import numpy as np  # noqa: E402

from verimem import embedding  # noqa: E402

VERE = [  # stesso soggetto, valore aggiornato
    ("Der Jahresplan kostet 100 Euro.", "Der Jahresplan kostet 200 Euro."),
    ("Der Server hat 8 Kerne.", "Der Server hat 16 Kerne."),
    ("Die Datenbank ist ein Postgres Cluster.",
     "Die Datenbank ist ein MySQL Cluster."),
    ("O plano anual custa 100 euros.", "O plano anual custa 200 euros."),
    ("Serwer ma 8 rdzeni.", "Serwer ma 16 rdzeni."),
    ("Sunucu 8 cekirdege sahiptir.", "Sunucu 16 cekirdege sahiptir."),
]

FALSE = [  # osservazioni scorrelate
    ("Der Graph hat 8625 Knoten.", "Die Quarantaene haelt 528 Fakten zurueck."),
    ("Der Server hat 8 Kerne.", "Das Repository hat 113 Commits."),
    ("Die Datenbank ist ein Postgres Cluster.",
     "Der Korpus enthaelt 6682 Fakten."),
    ("O grafo tem 8625 nos.", "A quarentena retem 528 fatos."),
    ("Serwer ma 8 rdzeni.", "Repozytorium ma 113 commitow."),
    ("Sunucu 8 cekirdege sahiptir.", "Depo 113 commit iceriyor."),
]


def cos(a: str, b: str) -> float:
    va, vb = embedding.encode(a), embedding.encode(b)
    va, vb = np.asarray(va, dtype=float), np.asarray(vb, dtype=float)
    return float(va @ vb / (np.linalg.norm(va) * np.linalg.norm(vb)))


print("=== COPPIE VERE (devono stare ALTE) ===")
sv = []
for a, b in VERE:
    c = cos(a, b)
    sv.append(c)
    print(f"  {c:.4f}  {a[:40]:<42} | {b[:40]}")

print("\n=== COPPIE FALSE (devono stare BASSE) ===")
sf = []
for a, b in FALSE:
    c = cos(a, b)
    sf.append(c)
    print(f"  {c:.4f}  {a[:40]:<42} | {b[:40]}")

print()
print(f"vere : min {min(sv):.4f}  max {max(sv):.4f}")
print(f"false: min {min(sf):.4f}  max {max(sf):.4f}")
sep = min(sv) - max(sf)
print(f"SEPARAZIONE (min vere - max false): {sep:+.4f}")
if sep > 0:
    print(f"  -> una soglia esiste, e sta fra {max(sf):.4f} e {min(sv):.4f}")
    print(f"  -> punto medio: {(max(sf) + min(sv)) / 2:.4f}")
else:
    print("  -> NESSUNA soglia separa i due gruppi: la strada non regge cosi'")
