# -*- coding: utf-8 -*-
"""IL LIMITE CHE HO DICHIARATO ALLE 19:27: due generi non sono una popolazione.

Alle 19:27 ho misurato che sul documento TECNICO il giudice da' 98.2 e 99.3 a
una cifra inventata (a fermarla e' la sola `L4.1`, con
`withheld_despite_judge=True`), mentre sul CONTRATTO resta sotto 12.2 e compare
sempre anche `L4-grounding`. E ho dichiarato il limite nello stesso post: due
generi non fanno una popolazione.

Qui ce ne sono quattro, e il quarto e' quello che conta di piu' per questo
prodotto: **il log di uno strumento**. La memoria di un agente non e' fatta di
contratti — e' fatta di output di comandi, tracce, ricevute. Se il log si
comporta come il documento tecnico, il regime peggiore e' quello del cliente
principale, e la riga smette di essere una congettura.

  tecnico    documento reale del repo (prosa tecnica con codice e numeri)
  contratto  articoli numerati, prosa giuridica
  referto    prosa clinica con valori e unita' di misura
  log        righe con timestamp, livello, modulo, contatori

Per ogni genere un claim della stessa forma: una cifra che la fonte NON contiene,
attribuita a un soggetto che la fonte nomina.

CONTROLLI CHE DEVONO POTER FALLIRE: a ogni lunghezza e per ogni genere, la cifra
del claim deve essere assente e il soggetto presente.

Il tecnico e' reale; contratto, referto e log sono costruiti nella forma del
loro genere, e lo dichiaro.

    python docs/stato-reale/banchi/quattro-generi-di-fonte.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

DOC = Path("docs/archive/2026-05-13_FORGIA.md")

CONTRATTO = [
    "Art. 3 - La penale per il ritardo nella consegna e' pari al 2% dell'importo contrattuale.",
    "Art. 4 - La penale per difformita' qualitativa e' pari al 7% dell'importo contrattuale.",
    "Art. 5 - Il termine di consegna e' fissato al 12 marzo 2027.",
    "Art. 7 - L'importo contrattuale e' di 148000 euro.",
    "Art. 8 - La cauzione definitiva e' pari a 22000 euro.",
    "Le parti danno atto di aver preso visione integrale del presente accordo.",
    "Il foro competente per ogni controversia e' quello della sede del committente.",
    "Le comunicazioni fra le parti avvengono a mezzo di posta elettronica certificata.",
    "Il presente atto e' redatto in duplice originale, uno per ciascuna parte.",
    "Le modifiche al presente accordo sono valide solo se pattuite per iscritto.",
]

REFERTO = [
    "Esame ematochimico eseguito a digiuno presso il laboratorio analisi.",
    "La glicemia basale risulta 104 mg/dl.",
    "Il colesterolo totale risulta 187 mg/dl.",
    "La creatinina risulta 82 micromoli per litro.",
    "L'emoglobina risulta 141 grammi per litro.",
    "Il paziente riferisce buona tolleranza alla terapia in corso.",
    "Non si segnalano reazioni avverse nel periodo di osservazione.",
    "Si consiglia controllo periodico secondo il calendario condiviso.",
    "La pressione arteriosa e' stata rilevata in condizioni di riposo.",
    "Il quadro complessivo appare stabile rispetto al controllo precedente.",
]

LOG = [
    "2026-08-20T09:14:22 INFO  auth        sessioni aperte 37",
    "2026-08-20T09:14:23 INFO  storage     righe scritte 512",
    "2026-08-20T09:14:25 WARN  auth        tentativi falliti 12",
    "2026-08-20T09:14:27 INFO  scheduler   job in coda 6",
    "2026-08-20T09:14:31 INFO  storage     compattazione completata",
    "2026-08-20T09:14:33 INFO  auth        token rinnovati",
    "2026-08-20T09:14:35 DEBUG scheduler   ciclo di controllo terminato",
    "2026-08-20T09:14:39 INFO  storage     indice aggiornato",
    "2026-08-20T09:14:41 DEBUG auth        cache riscaldata",
    "2026-08-20T09:14:44 INFO  scheduler   nessun errore rilevato",
]

# (genere, righe, claim, cifra che deve essere ASSENTE, soggetto che deve esserci)
GENERI = {
    "contratto": (CONTRATTO, "La cauzione definitiva e' pari a 91111 euro.", "91111", "cauzione"),
    "referto": (REFERTO, "La glicemia basale risulta 92222 mg/dl.", "92222", "glicemia"),
    "log": (LOG, "Il modulo auth ha registrato 93333 tentativi falliti.", "93333", "auth"),
}
CLAIM_TEC = "Il file wake.py conta 94444 LOC."

LUNGHEZZE = [1000, 2000, 4000, 6000]


def _monta(righe: list[str], n: int) -> str:
    pezzi, i = [], 0
    while len(" ".join(pezzi)) < n:
        pezzi.append(righe[i % len(righe)])
        i += 1
    return " ".join(pezzi)[:n]


def main() -> int:
    if not DOC.exists():
        print(f"NON RIUSCITO: {DOC} non c'e'")
        return 1
    tecnico = DOC.read_text(encoding="utf-8", errors="replace")

    fonti = {}
    for n in LUNGHEZZE:
        t = tecnico[:n]
        if "94444" in t or "wake.py" not in t:
            print(f"CONTROLLO CADUTO tecnico a {n}")
            return 1
        fonti[("tecnico", n)] = (t, CLAIM_TEC)
        for g, (righe, claim, cifra, sogg) in GENERI.items():
            f = _monta(righe, n)
            if cifra in f or sogg not in f:
                print(f"CONTROLLO CADUTO {g} a {n}: cifra presente={cifra in f}, "
                      f"soggetto presente={sogg in f}")
                return 1
            fonti[(g, n)] = (f, claim)
    print(f"  CONTROLLO retto: {len(fonti)} celle, cifra assente e soggetto presente ovunque")

    from verimem import client as _client  # noqa: PLC0415
    from verimem.client import Memory  # noqa: PLC0415

    print(f"  codice sotto misura: {_client.__file__}")
    print("  tecnico REALE; contratto, referto e log costruiti nella forma del genere\n")
    mem = Memory(str(Path(tempfile.mkdtemp()) / "generi.db"))

    ordine = ["tecnico", "contratto", "referto", "log"]
    print("  " + f"{'genere':<11}" + "".join(f"{n:>9}" for n in LUNGHEZZE) + "   ampiezza  solo-L4.1")
    print("  " + "-" * 62)
    for g in ordine:
        celle, solo_regex = [], 0
        for n in LUNGHEZZE:
            fonte, claim = fonti[(g, n)]
            ric = mem.add(claim, topic=f"gg/{g}/{n}", source=fonte, validate="full")
            sc = float(ric.get("grounding_score") or -1)
            st = str(ric.get("status"))
            celle.append((st != "quarantined", sc))
            # la difesa e' SINGOLA quando il giudice ha detto sostenuto
            if str(ric.get("warnings", "")).find("L4-grounding") < 0 and sc > 80:
                solo_regex += 1
        gs = [x for _e, x in celle]
        amp = max(gs) - min(gs)
        riga = "".join(f"{('E' if e else '') + f'{x:.1f}':>9}" for e, x in celle)
        print(f"  {g:<11}{riga}   {amp:>7.1f}   {solo_regex} su {len(LUNGHEZZE)}")

    print("\n  Nota: «solo-L4.1» conta le celle in cui il giudice ha dato piu' di 80")
    print("  a una cifra INVENTATA — li' la difesa e' la sola regex.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
