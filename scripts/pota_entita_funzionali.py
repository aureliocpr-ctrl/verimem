"""Toglie dal grafo le entita' che l'estrattore di oggi non produrrebbe piu'.

IL PROBLEMA. `entity_extract_lite` prende come `acronym` qualunque parola di
2-6 lettere tutta maiuscola, e nei nostri fatti le maiuscole sono ENFASI: «il
gate NON ha girato». La cura c'e' — dal 2026-08-01 le parole funzionali urlate
vengono scartate riusando `_PAROLE_VUOTE` — ma vale IN AVANTI. Il grafo
costruito prima se le tiene:

    entita totali        8810
      TUTTE MAIUSCOLE    1486 (16.9%)
      loro collegamenti  9379 su 27641

    l'entita con piu' fatti collegati e' «NON», 418

e il PPR cammina su quel grafo. `scripts/backfill_entity_graph.py` e'
idempotente ma POPOLA: rieseguirlo non toglie niente.

IL CRITERIO E' ESATTAMENTE QUELLO DELLA CURA, non un'euristica nuova: un
`acronym` il cui nome minuscolo sta in `_PAROLE_VUOTE`. Se domani la cura
cambia, cambia anche questa potatura — non c'e' una seconda definizione da
tenere allineata.

DRY-RUN DI DEFAULT. Il grafo e' un indice DERIVATO e si ricostruisce dal
corpus, ma resta un dato di Aurelio: senza `--apply` questo script misura,
elenca e non tocca niente.

    python scripts/pota_entita_funzionali.py            # dice cosa toglierebbe
    python scripts/pota_entita_funzionali.py --apply    # lo toglie
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from verimem.document_index import _PAROLE_VUOTE  # noqa: E402

KG = Path.home() / ".engram" / "entity_kg" / "entity_kg.db"


def _da_potare(con: sqlite3.Connection) -> list[tuple[str, str, int]]:
    """(id, nome, quanti fatti) per ogni entita' che la cura scarterebbe."""
    conteggi = dict(con.execute(
        "SELECT entity_id, COUNT(*) FROM entity_facts GROUP BY entity_id"))
    fuori = []
    for eid, nome, tipo in con.execute(
            "SELECT id, canonical_name, type FROM entities"):
        if tipo == "acronym" and (nome or "").lower() in _PAROLE_VUOTE:
            fuori.append((eid, nome, conteggi.get(eid, 0)))
    return sorted(fuori, key=lambda x: -x[2])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true",
                    help="rimuove davvero; senza, misura e basta")
    ap.add_argument("--db", default=str(KG))
    args = ap.parse_args()

    db = Path(args.db)
    if not db.exists():
        print(f"nessun grafo in {db}")
        return 1

    con = sqlite3.connect(str(db))
    try:
        tot_ent = con.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
        tot_link = con.execute("SELECT COUNT(*) FROM entity_facts").fetchone()[0]
        tot_edge = con.execute("SELECT COUNT(*) FROM entity_edges").fetchone()[0]
        fuori = _da_potare(con)
        ids = [e for e, _, _ in fuori]

        print(f"grafo: {tot_ent} entita, {tot_link} collegamenti, "
              f"{tot_edge} archi")
        print(f"da potare: {len(fuori)} entita "
              f"({sum(n for _, _, n in fuori)} collegamenti)")
        for _eid, nome, n in fuori[:15]:
            print(f"   {n:5d}  {nome}")
        if len(fuori) > 15:
            print(f"   … e altre {len(fuori) - 15}")

        if not ids:
            print("niente da fare")
            return 0
        if not args.apply:
            print("\nDRY-RUN: niente e' stato toccato. `--apply` per potare.")
            return 0

        q = ",".join("?" * len(ids))
        con.execute(f"DELETE FROM entity_facts WHERE entity_id IN ({q})", ids)
        con.execute(
            f"DELETE FROM entity_edges WHERE src_entity IN ({q}) "
            f"OR dst_entity IN ({q})", (*ids, *ids))
        con.execute(f"DELETE FROM entity_aliases WHERE entity_id IN ({q})", ids)
        con.execute(f"DELETE FROM entity_attrs WHERE entity_id IN ({q})", ids)
        con.execute(f"DELETE FROM entities WHERE id IN ({q})", ids)
        con.commit()

        print(f"\npotate {len(ids)} entita")
        print(f"  entita      {tot_ent} -> "
              f"{con.execute('SELECT COUNT(*) FROM entities').fetchone()[0]}")
        print(f"  collegamenti {tot_link} -> "
              f"{con.execute('SELECT COUNT(*) FROM entity_facts').fetchone()[0]}")
        print(f"  archi        {tot_edge} -> "
              f"{con.execute('SELECT COUNT(*) FROM entity_edges').fetchone()[0]}")
    finally:
        con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
