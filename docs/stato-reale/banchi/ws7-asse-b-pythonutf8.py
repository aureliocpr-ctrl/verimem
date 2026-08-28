# -*- coding: utf-8 -*-
"""ASSE B — `PYTHONUTF8=1` cambia il verdetto del gate su testo italiano?

PERCHE' ESISTE. Il 28/08 ho censito i verdi del registro cercando quali
reggessero solo «in casa nostra», e avevo guardato UN asse solo:
`HIPPO_ENCODE_DELEGATE_ONLY`. @ws6 alle 20:20 ha misurato l'ambiente e ne ha
trovato un secondo, che nessuno aveva rimisurato dal 20/08:

    PYTHONUTF8=1   acceso sulle nostre macchine, SPENTO in CI
                   -- e fu la causa di un rosso che «non si riproduceva»

Non e' una variabile del prodotto: e' dell'INTERPRETE. Questo la rende piu'
insidiosa, non meno: nessuna cella del registro dichiara nel proprio regime se
fosse accesa, e per una misura su testo italiano e' la differenza fra
riprodursi e non riprodursi.

COSA MISURA, e cosa NON misura. Misura l'ASSE, non le celle: le dieci celle a
rischio (`4 14 15 16 29 32 33 44 W7-19 53`) sono di altre e i loro banchi non
li conosco. Se le due esecuzioni coincidono, quelle dieci non hanno bisogno di
essere rifatte per QUESTA ragione; se differiscono, questo banco e' il caso
riproducibile che dice a chi le ha scritte cosa guardare.

LE DUE POPOLAZIONI, che vanno misurate entrambe (un veto le vuole tutte e due):
    VERO  un claim che la fonte sostiene  -> deve essere AMMESSO
    FALSO un claim con una cifra inventata -> deve essere FERMATO
e ognuna in due forme: CON accenti e SENZA. Cosi' una differenza fra i due
regimi si attribuisce agli accenti e non alla frase.

LA SECONDA DOMANDA, nello stesso banco. Le mie tre scritture di stasera sono
state quarantinate con `grounding_score` fra 99,87 e 99,98 e
`withheld_despite_judge=True`. Leggevo quel campo come «il gate non crede alla
fonte»: @ws1 alle 21:05 mi ha corretto la domanda -- il giudice diceva SI', a
fermarmi e' stato un layer lessicale. Quindi qui le rifaccio per vedere COSA
VEDE `L4.1`, che e' una domanda diversa da quella che mi ero fatta.

    con    PYTHONUTF8=1 python docs/stato-reale/banchi/ws7-asse-b-pythonutf8.py
    senza  env -u PYTHONUTF8 python docs/stato-reale/banchi/ws7-asse-b-pythonutf8.py

Il banco stampa il proprio regime (variabile e codec effettivi), cosi' il
confronto e' leggibile senza fidarsi di chi lo ha lanciato. Gira FUORI da
pytest di proposito: sotto pytest l'embedder e' uno stub su SHA-256
(`conftest._stub_embedding_model`) e misurerebbe il righello.

Store TEMPORANEO via `HIPPO_DATA_DIR` -- e' quella che isola davvero, mentre
`ENGRAM_DATA_DIR` no. Mai quello di Aurelio.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

FONTE_ACC = (
    "Verbale del 12 marzo. La perizia e' stata depositata in cancelleria e "
    "l'importo liquidato al perito e' di 1450 euro. Il giudice ha disposto che "
    "la societa' produca l'elenco integrale dei beni entro trenta giorni."
)
FONTE_NUD = (
    "Verbale del 12 marzo. La perizia e stata depositata in cancelleria e "
    "l importo liquidato al perito e di 1450 euro. Il giudice ha disposto che "
    "la societa produca l elenco integrale dei beni entro trenta giorni."
)

#: (etichetta, claim, fonte, atteso)  -- atteso: quello che il gate DOVREBBE fare
CASI = [
    ("VERO  con accenti", "L'importo liquidato al perito e' di 1450 euro.", FONTE_ACC, "admitted"),
    ("VERO  senza accenti", "L importo liquidato al perito e di 1450 euro.", FONTE_NUD, "admitted"),
    ("FALSO con accenti", "L'importo liquidato al perito e' di 9999 euro.", FONTE_ACC, "quarantined"),
    ("FALSO senza accenti", "L importo liquidato al perito e di 9999 euro.", FONTE_NUD, "quarantined"),
]

#: le tre frasi vere di stasera, quarantinate con grounding fra 99,87 e 99,98
FONTE_MIA = (
    "$ python scripts/conta_celle_esame.py\n"
    "rossi 58 - verdi 29 - parziali 17 - non misurabili 1 - ritirate 1   (su 106 celle)\n"
    "id duplicati: W7-20"
)
MIE = [
    ("mia 1 (con identificatore)",
     "Lo script scripts/conta_celle_esame.py eseguito sul registro 00-ESAME.md "
     "stampa la riga «id duplicati: W7-20».", FONTE_MIA),
    ("mia 2 (senza identificatore)",
     "Lo script scripts/conta_celle_esame.py eseguito sul registro 00-ESAME.md "
     "stampa una riga che elenca gli id duplicati.", FONTE_MIA),
    ("mia 3 (senza virgolette basse)",
     "Lo script scripts/conta_celle_esame.py stampa una riga che elenca gli id duplicati.",
     FONTE_MIA),
]


def _regime() -> str:
    var = os.environ.get("PYTHONUTF8", "(assente)")
    return (
        f"PYTHONUTF8={var} · stdout={sys.stdout.encoding} · "
        f"fs={sys.getfilesystemencoding()} · utf8_mode={sys.flags.utf8_mode}"
    )


def _riga(mem, etichetta: str, claim: str, fonte: str, topic: str) -> tuple:
    ric = mem.add(claim, topic=topic, source=fonte, validate="full")
    stato = str(ric.get("status"))
    ground = float(ric.get("grounding_score") or -1)
    strati = ric.get("by_layer") or ric.get("layers") or ric.get("anti_confab_warnings") or []
    if isinstance(strati, dict):
        strati = sorted(strati)
    print(f"  {etichetta:<28} {stato:<12} {ground:7.2f}   {strati}")
    return etichetta, stato, ground


def main() -> int:
    print(f"\n  REGIME: {_regime()}\n")

    # Controllo che DEVE poter fallire: la cifra inventata non sta nelle fonti.
    for nome, fonte in (("ACC", FONTE_ACC), ("NUD", FONTE_NUD)):
        if "9999" in fonte:
            print(f"  CONTROLLO CADUTO: 9999 e' dentro la fonte {nome}")
            return 1
    print("  controllo retto: la cifra inventata non e' in nessuna delle due fonti")
    # e il secondo controllo: le due fonti devono differire SOLO per gli accenti
    if FONTE_ACC == FONTE_NUD:
        print("  CONTROLLO CADUTO: le due fonti sono identiche")
        return 1
    print("  controllo retto: le due fonti differiscono\n")

    from verimem import client as _client  # noqa: PLC0415
    from verimem.client import Memory  # noqa: PLC0415

    print(f"  codice sotto misura: {_client.__file__}\n")
    mem = Memory(str(Path(tempfile.mkdtemp()) / "asse_b.db"))

    print(f"  {'caso':<28} {'esito':<12} {'ground':>7}   layer")
    print("  " + "-" * 72)
    esiti = [_riga(mem, e, c, f, f"asseB/{i}") for i, (e, c, f, _a) in enumerate(CASI)]
    print()
    esiti += [_riga(mem, e, c, f, f"asseB/mia{i}") for i, (e, c, f) in enumerate(MIE)]

    atteso_ok = sum(1 for (e, s, _g), (_l, _c, _f, a) in zip(esiti[:4], CASI) if s == a)
    trattenute = sum(1 for _e, s, _g in esiti[4:] if s == "quarantined")
    print(
        f"\n  RIGA DA CONFRONTARE FRA I DUE REGIMI: "
        f"attesi rispettati {atteso_ok}/4 · mie trattenute {trattenute}/3 · "
        f"utf8_mode={sys.flags.utf8_mode}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
