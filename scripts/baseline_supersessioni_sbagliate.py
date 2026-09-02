"""BASELINE M3 — quanti fatti VERI il consolidamento ha ritirato.

Anello ① della catena: un comando che chiunque può rifare sul commit corrente.

    python scripts/baseline_supersessioni_sbagliate.py

CRITERIO DICHIARATO, ed è quello del fatto `29b35cf2386b` e non altro:
un fatto ritirato si dice «vero» se il giudice lo sosteneva, cioè se il suo
`grounding_score` è >= 90. Il confronto che rende leggibile il numero sono i
TRE profili insieme — i due motivi di ritiro e la popolazione mai ritirata:
senza il terzo non si sa se 98,9% sia alto.

⚠️ NON è il criterio «numeri diversi fra vecchio e nuovo» usato in `W2-369`
(che dava 84,3% su 395): quello misura se il testo cambia, questo se il fatto
ritirato era sostenuto. Sono due domande diverse e vanno tenute separate.

Sola lettura: apre lo store con mode=ro e non scrive nulla.
"""
from __future__ import annotations

import os
import sqlite3

DB = os.path.join(os.environ["USERPROFILE"], ".engram", "semantic", "semantic.db")


def quota(con: sqlite3.Connection, dove: str) -> tuple[int, int, float]:
    n, k = con.execute(
        "SELECT COUNT(*), SUM(CASE WHEN grounding_score >= 90 THEN 1 ELSE 0 END) "
        "FROM facts WHERE grounding_score IS NOT NULL AND " + dove).fetchone()
    k = k or 0
    return n, k, (100.0 * k / n if n else 0.0)


def main() -> int:
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    print("  BASELINE M3 — il consolidamento ritira fatti che il giudice sosteneva")
    print("  criterio: grounding_score >= 90 fra i ritirati, per motivo di ritiro")
    print()
    righe = [
        ("ritirati da same-source evolution", "superseded_reason LIKE 'same-source%'"),
        ("ritirati da numeric_clash        ", "superseded_reason LIKE '%numeric_clash%'"),
        ("MAI superseduti (controllo)      ", "superseded_by IS NULL"),
    ]
    for eti, dove in righe:
        n, k, pc = quota(con, dove)
        print(f"  {eti}  n={n:5d} · con grounding>=90: {k:5d} · {pc:5.1f}%")
    tot = con.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
    sup = con.execute("SELECT COUNT(*) FROM facts WHERE superseded_by IS NOT NULL").fetchone()[0]
    print()
    print(f"  corpus: {tot} fatti · superseduti in tutto: {sup}")
    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
