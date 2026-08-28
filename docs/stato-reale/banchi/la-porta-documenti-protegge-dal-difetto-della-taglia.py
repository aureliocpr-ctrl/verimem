# -*- coding: utf-8 -*-
"""LA CURA ESISTE GIA' NEL PRODOTTO? La porta documenti contro la taglia.

Alle 20:10 ho misurato che gli stessi fatti VERI passano quando la fonte e' la
riga che li sostiene (4 su 4) e vengono rifiutati quando quella riga sta dentro
il documento intero (1 su 4). Falso negativo per diluizione, su fonte reale
fissata.

Ma il prodotto ha una porta apposta per i documenti — `index_document` e
`search_documents` — che li spezza in pezzi. ⇒ se quella porta protegge, la cura
esiste gia' e il difetto colpisce solo chi passa il documento intero come
`source`; se non protegge, il difetto sta nel percorso che il prodotto stesso
raccomanda per i documenti.

E' il paragone che mi compete: il prodotto PROMETTE una porta per i documenti;
questo banco guarda se quella porta FA quello che serve.

Le due vie, sugli stessi quattro fatti veri e sullo stesso documento:

  DIRETTA   `add(claim, source=<documento intero>)`   — gia' misurata: 1 su 4
  PORTA     `index_document(<file>)` e poi `search_documents(<claim>)`, e si
            guarda se il pezzo restituito contiene la riga che sostiene il fatto

CONTROLLI CHE DEVONO POTER FALLIRE: il documento dev'essere indicizzato davvero
(se `index_document` fallisce, il banco lo dice invece di misurare il vuoto) e i
fatti devono essere gli stessi delle 20:10.

Fonte FISSATA su file, committata: `banchi/fonte-log-fissata.txt`.

    python docs/stato-reale/banchi/la-porta-documenti-protegge-dal-difetto-della-taglia.py
"""

from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path

FONTE_FILE = Path("docs/stato-reale/banchi/fonte-log-fissata.txt")
QUANTI = 4


def main() -> int:
    if not FONTE_FILE.exists():
        print(f"NON RIUSCITO: {FONTE_FILE} non c'e'")
        return 1
    righe = FONTE_FILE.read_text(encoding="utf-8", errors="replace").splitlines()
    log = " ".join(x.strip() for x in righe if x.strip()).replace("@@", "")

    voci, corrente = [], None
    for riga in righe:
        r = riga.strip()
        if r.startswith("@@"):
            _h, _, s = r[2:].partition("|")
            corrente = s
        elif "insertion" in r and corrente:
            m = re.search(r"(\d+) insertion", r)
            if m:
                voci.append((corrente, m.group(1), r.strip()))
            corrente = None
    buoni = [
        (s, c, r) for s, c, r in voci
        if len(re.findall(rf"\b{c}\b", log)) == 1 and 20 < len(s) < 70 and log.find(s[:30]) >= 0
    ]
    if len(buoni) < QUANTI:
        print(f"NON RIUSCITO: fatti buoni {len(buoni)}")
        return 1
    buoni.sort(key=lambda x: log.find(x[0][:30]))
    scelti = buoni[:QUANTI]
    print(f"  fonte FISSATA: {len(log)} caratteri · {QUANTI} fatti veri, gli stessi delle 20:10\n")

    from verimem import client as _client  # noqa: PLC0415
    from verimem.client import Memory  # noqa: PLC0415

    print(f"  codice sotto misura: {_client.__file__}\n")
    tmp = Path(tempfile.mkdtemp())
    mem = Memory(str(tmp / "porta.db"))

    # il documento su disco, cosi' come la porta lo vuole
    doc = tmp / "log-fissato.txt"
    doc.write_text(log, encoding="utf-8")
    try:
        esito_index = mem.index_document(doc)
    except Exception as e:  # noqa: BLE001
        print(f"CONTROLLO CADUTO: index_document ha sollevato {type(e).__name__}: {e}")
        return 1
    print(f"  index_document -> {str(esito_index)[:120]}")
    if not esito_index:
        print("CONTROLLO CADUTO: index_document non ha restituito nulla di utile")
        return 1
    print()

    print(f"  {'ins':>6}   {'DIRETTA (documento intero)':>28}   {'PORTA: il pezzo ha la riga?':>30}")
    print("  " + "-" * 74)
    diretta_ok = porta_ok = 0
    for sog, ins, riga_conteggio in scelti:
        claim = f"Il commit «{sog}» ha aggiunto {ins} inserzioni."

        ric = mem.add(claim, topic=f"pd/diretta/{ins}", source=log, validate="full")
        g = float(ric.get("grounding_score") or -1)
        st = str(ric.get("status"))
        if st != "quarantined":
            diretta_ok += 1
        cella_d = f"{'ENTRA' if st != 'quarantined' else 'ferma'} {g:6.1f}"

        try:
            pezzi = mem.search_documents(claim, k=3)
        except Exception as e:  # noqa: BLE001
            print(f"  {ins:>6}   {cella_d:>28}   search_documents: {type(e).__name__}")
            continue
        testi = []
        for p in pezzi or []:
            if isinstance(p, dict):
                testi.append(str(p.get("text") or p.get("chunk") or p.get("content") or ""))
            else:
                testi.append(str(p))
        trovato = any(ins in t and sog[:25] in t for t in testi)
        if trovato:
            porta_ok += 1
        cella_p = f"{'SI, in ' + str(len(testi)) + ' pezzi' if trovato else 'no (' + str(len(testi)) + ' pezzi)'}"
        print(f"  {ins:>6}   {cella_d:>28}   {cella_p:>30}")

    print(f"\n  DIRETTA  {diretta_ok} su {QUANTI} fatti veri ammessi")
    print(f"  PORTA    {porta_ok} su {QUANTI} volte il pezzo restituito contiene la prova")

    print()
    if porta_ok >= QUANTI - 1 and diretta_ok <= 1:
        print("  => LA CURA ESISTE GIA': la porta documenti restituisce il pezzo che")
        print("     contiene la prova, mentre la via diretta col documento intero rifiuta")
        print("     i fatti veri. ⇒ il difetto della taglia colpisce chi passa il")
        print("     documento come `source`, non chi usa `index_document`.")
    elif porta_ok <= 1:
        print("  => LA PORTA NON PROTEGGE: nemmeno indicizzando il documento il pezzo")
        print("     che sostiene il fatto viene restituito. Il difetto sta nel percorso")
        print("     che il prodotto stesso raccomanda per i documenti.")
    else:
        print(f"  => quadro intermedio: DIRETTA {diretta_ok}/{QUANTI}, PORTA {porta_ok}/{QUANTI}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
