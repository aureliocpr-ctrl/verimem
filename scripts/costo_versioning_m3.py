"""M3 — quanto costa VERSIONARE invece di ritirare, e quanti fatti tornano.

    python scripts/costo_versioning_m3.py          (sola lettura)

Risponde alle due domande dell'anello ③ con un comando che chiunque rifà.

⚠️ IL FRAMING DEL MANDATO VA CORRETTO PRIMA DI MISURARE.
«`supersede()` come append di una riga-versione» suggerisce di AGGIUNGERE righe.
Non serve: i fatti ritirati **sono già nel database** — pesano 10,3 MB su 124,9 e
nessuno li ha cancellati. Il ritiro è un CAMPO (`superseded_by`), non una
delete. Quindi il costo del versioning non è la duplicazione dei fatti: sono le
due colonne temporali (`valid_from` / `valid_to`) su ogni riga.

⚠️ E «zero fatti persi» è una tautologia: se non si cancella nulla, nulla si
perde. La domanda che decide è **quanti tornano SERVIBILI**, e la risposta non è
un `COUNT(*)`: dipende da quanti dei ritirati siano ancora sostenuti dal
giudice. Per questo il conto qui sotto separa i ritirati per stato.
"""
from __future__ import annotations

import os
import sqlite3

DB = os.path.join(os.environ["USERPROFILE"], ".engram", "semantic", "semantic.db")


def main() -> int:
    peso = os.path.getsize(DB)
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    uno = con.execute
    tot = uno("SELECT COUNT(*) FROM facts").fetchone()[0]
    sup = uno("SELECT COUNT(*) FROM facts WHERE superseded_by IS NOT NULL").fetchone()[0]
    bs = uno("SELECT SUM(LENGTH(COALESCE(proposition,'')) + "
             "LENGTH(COALESCE(embedding,''))) FROM facts "
             "WHERE superseded_by IS NOT NULL").fetchone()[0] or 0

    print(f"  DB su disco {peso / 1048576:.1f} MB · fatti {tot} · ritirati {sup}")
    print(f"  i ritirati SONO GIA' nel DB e pesano {bs / 1048576:.1f} MB: "
          "il versioning non li duplica")
    costo = tot * 16  # due REAL per riga
    print(f"  COSTO = due colonne temporali su {tot} righe = "
          f"{costo / 1048576:.2f} MB = {100.0 * costo / peso:.2f}% del DB")
    print()

    print("  QUANTI RITIRATI TORNEREBBERO SERVIBILI — per stato, non in blocco")
    for eti, dove in (
            ("sostenuti (grounding >= 90)", "grounding_score >= 90"),
            ("MAI giudicati              ", "grounding_score IS NULL"),
            ("quarantinati               ", "status = 'quarantined'")):
        n = uno("SELECT COUNT(*) FROM facts WHERE superseded_by IS NOT NULL "
                f"AND {dove}").fetchone()[0]
        print(f"     {eti}  {n:5d}  ({100.0 * n / sup:5.1f}%)")
    print()

    serviti = uno("SELECT COUNT(*) FROM facts WHERE superseded_by IS NULL "
                  "AND status <> 'quarantined'").fetchone()[0]
    rec = uno("SELECT COUNT(*) FROM facts WHERE superseded_by IS NOT NULL "
              "AND grounding_score >= 90 AND status <> 'quarantined'").fetchone()[0]
    print(f"  fatti serviti oggi        {serviti:5d}  ({100.0 * serviti / tot:.1f}% del corpus)")
    print(f"  + ritirati sostenuti e non quarantinati {rec:5d}")
    print(f"  = con il versioning       {serviti + rec:5d}  "
          f"({100.0 * (serviti + rec) / tot:.1f}%)  "
          f"guadagno {100.0 * rec / tot:.1f} punti")
    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
