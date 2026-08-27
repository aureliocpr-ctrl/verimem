# -*- coding: utf-8 -*-
"""L'IPOTESI CHE HO DICHIARATO ALLE 21:30, e che tocca a me chiudere.

Due miei banchi di stasera dicono cose opposte sullo STESSO tipo di claim — uno
che afferma una cifra che la fonte non dice:

  20:19  fonte = UNA FRASE («Su 40 pezzi controllati, 30 sono risultati
         difformi»), claim «Solo 3 pezzi» -> ground 0.6, sette scritture su sette
  21:28  fonte = 6000 caratteri di documento, claim «9999 LOC» -> ground 99.3

Fra le due c'erano tre variabili confuse: la lunghezza, la natura della fonte
(frase costruita contro documento reale) e il tipo di claim (una quantita'
contro un identificatore). Questo banco ne isola UNA: **la lunghezza**. Stessa
frase-fonte, stesso claim, e in coda altre frasi dello stesso verbale — testo
PERTINENTE, non contorno estraneo, perche' la natura del contorno l'avevo gia'
esclusa nel dossier ⑩.

Se a 50 caratteri il claim numerico falso prende 0.6 e a 4000 prende 99, allora
il giudice smette di vedere la cifra quando la fonte si allunga, e l'unica
difesa che resta e' `L4.1` — che e' il punto singolo che @ws3 ha nominato: se
cade quello, nessun altro layer raccoglie.

Se invece resta basso a ogni lunghezza, l'ipotesi cade e la differenza fra i due
banchi va cercata nel TIPO di claim, non nella lunghezza.

CONTROLLO CHE DEVE POTER FALLIRE: ogni fonte deve contenere «40» e «30» e non
deve MAI contenere un «3» isolato — altrimenti non sto allungando la fonte, sto
cambiando quello che L4.1 ci trova dentro.

    python docs/stato-reale/banchi/la-cifra-sparisce-quando-la-fonte-si-allunga.py
"""

from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path

BASE = "Su 40 pezzi controllati, 30 sono risultati difformi."
CLAIM = "Solo 3 pezzi sono risultati difformi."

# Frasi dello stesso verbale: pertinenti, prive di cifre, cosi' che l'unica cosa
# che cambia sia quanto testo circonda la frase che porta la prova.
CODA = [
    "Il collaudo si e' svolto nel reparto di assemblaggio alla presenza del responsabile di linea.",
    "Le difformita' riscontrate riguardano la finitura superficiale e la tolleranza dimensionale.",
    "Il campione e' stato prelevato secondo la procedura interna vigente per i lotti in ingresso.",
    "Gli strumenti di misura impiegati risultavano tarati e in corso di validita'.",
    "Il responsabile di reparto ha controfirmato il verbale al termine delle operazioni.",
    "Le anomalie sono state fotografate e allegate al fascicolo del lotto.",
    "La linea e' stata fermata per il tempo necessario alle verifiche supplementari.",
    "Il fornitore e' stato informato per le vie ordinarie nella stessa giornata lavorativa.",
    "Copia del presente verbale e' stata trasmessa all'ufficio qualita' per gli adempimenti.",
    "Nessuna osservazione ulteriore e' stata formulata dalle parti presenti alle verifiche.",
]

LUNGHEZZE = [0, 200, 500, 1000, 2000, 4000, 8000]


def _fonte(n: int) -> str:
    """La frase con la prova, seguita da coda pertinente fino a ~n caratteri."""
    if n == 0:
        return BASE
    fuori = [BASE]
    i = 0
    while len(" ".join(fuori)) < n:
        fuori.append(CODA[i % len(CODA)])
        i += 1
    return " ".join(fuori)


def main() -> int:
    fonti = {}
    for n in LUNGHEZZE:
        f = _fonte(n)
        numeri = re.findall(r"\d+", f)
        if "40" not in numeri or "30" not in numeri:
            print(f"CONTROLLO CADUTO a {n}: la fonte non porta 40 e 30, ha {sorted(set(numeri))}")
            return 1
        if "3" in numeri:
            print(f"CONTROLLO CADUTO a {n}: nella fonte c'e' un 3 isolato")
            return 1
        fonti[n] = f
    print(f"  CONTROLLO retto: 40 e 30 in tutte le {len(LUNGHEZZE)} fonti, nessun 3 isolato")
    print(f"  claim, sempre lo stesso: «{CLAIM}»\n")

    from verimem.client import Memory  # noqa: PLC0415

    mem = Memory(str(Path(tempfile.mkdtemp()) / "diluizione.db"))

    print("  car.   esito         ground   quota-prova")
    print("  " + "-" * 48)
    out = []
    for n, fonte in fonti.items():
        ric = mem.add(CLAIM, topic=f"dil/{n}", source=fonte, validate="full")
        g = float(ric.get("grounding_score") or -1)
        st = str(ric.get("status"))
        quota = 100.0 * len(BASE) / len(fonte)
        out.append((len(fonte), st, g, quota))
        print(f"  {len(fonte):>5}   {st:<12} {g:6.1f}   {quota:5.1f}%  {'#' * int(g / 4)}")

    gs = [g for _n, _s, g, _q in out]
    print(f"\n  il grounding dello stesso claim falso va da {min(gs):.1f} a {max(gs):.1f}")
    corta = out[0][2]
    lunghe = [g for n, _s, g, _q in out if n >= 2000]
    print(f"  fonte nuda ({out[0][0]} car.): {corta:.1f}")
    print(f"  fonti da 2000 caratteri in su: {', '.join(f'{g:.1f}' for g in lunghe)}")
    if corta < 50 and lunghe and min(lunghe) > 50:
        print("\n  ⇒ L'IPOTESI REGGE: la stessa cifra falsa che sulla frase nuda viene")
        print("    respinta, diluita in un verbale pertinente prende un punteggio alto.")
        print("    Sulle fonti lunghe la difesa contro la cifra e' SOLO L4.1.")
    elif corta < 50 and lunghe and max(lunghe) < 50:
        print("\n  ⇒ L'IPOTESI CADE: resta basso a ogni lunghezza. La differenza fra i")
        print("    due banchi va cercata nel TIPO di claim, non nella lunghezza.")
    else:
        print("\n  ⇒ ne' l'uno ne' l'altro in modo netto: guarda i numeri.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
