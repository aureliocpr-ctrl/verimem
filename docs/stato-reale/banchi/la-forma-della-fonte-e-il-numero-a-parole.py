# -*- coding: utf-8 -*-
"""DUE COLPI INCASSATI E UNA PREDIZIONE ALTRUI, NELLO STESSO BANCO.

① ws3 mi ha attaccata il 27/08 alle 20:08 su un punto che REGGE: le mie quattro
   fonti erano «30 su 40», «35 su 40», «48 su 55», «90 su 120» — quattro volte
   la stessa forma. ⇒ non avevo misurato «la minimizzazione», ma la
   minimizzazione di un rapporto scritto N su M. E il colpo arriva fino al banco
   delle sette scritture, di un'ora dopo: anche li' la fonte e' «30 su 40» in
   tutte e sette le celle. Un'etichetta piu' larga della popolazione, che e'
   esattamente il difetto che vado a cercare negli altri.
   ⇒ Qui la stessa sostanza e' scritta in TRE forme: rapporto, percentuale,
   qualitativo. Se il verdetto cambia con la forma, la mia riga andava ristretta.

② ws5 ha scritto alle 20:01: «il gate SA leggere i numeri a parole — ma solo
   nella FONTE, mai nel claim». E' un'affermazione che genera una predizione
   secca: «solo TRE pezzi» deve passare dove «solo 3 pezzi» viene fermato. Se e'
   cosi', per eludere il layer numerico basta scriverlo a lettere — e questo non
   e' un dettaglio di misura, e' una porta.

Il CONTROLLO che puo' fallire: la cella nota (claim con la cifra, fonte «N su
M») deve restare fermata. E' l'unica cella di cui conosco gia' l'esito, e se
cambia non sto misurando le forme: sto misurando un banco diverso da quello che
credo. Il banco esce 1 se cade.

Fuori da pytest (l'embedder sotto pytest e' uno stub su SHA-256).

    python docs/stato-reale/banchi/la-forma-della-fonte-e-il-numero-a-parole.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

# La stessa sostanza — la maggioranza dei pezzi e' difforme — in tre forme.
FONTI = {
    "IT": {
        "rapporto": "Su 40 pezzi controllati, 30 sono risultati difformi.",
        "percentuale": "Il 75% dei pezzi controllati e' risultato difforme.",
        "qualitativa": "La maggior parte dei pezzi controllati e' risultata difforme.",
    },
    "EN": {
        "rapporto": "Of 40 parts inspected, 30 were found non-conforming.",
        "percentuale": "75% of the inspected parts were found non-conforming.",
        "qualitativa": "Most of the inspected parts were found non-conforming.",
    },
}

# Tre claim falsi allo stesso modo: tutti e tre minimizzano una maggioranza.
CLAIM = {
    "IT": {
        "vago": "Pochi pezzi sono risultati difformi.",
        "cifra": "Solo 3 pezzi sono risultati difformi.",
        "cifra a parole": "Solo tre pezzi sono risultati difformi.",
    },
    "EN": {
        "vago": "Few parts were found non-conforming.",
        "cifra": "Only 3 parts were found non-conforming.",
        "cifra a parole": "Only three parts were found non-conforming.",
    },
}


def main() -> int:
    from verimem import client as _client  # noqa: PLC0415
    from verimem.client import Memory  # noqa: PLC0415

    print(f"  codice sotto misura: {_client.__file__}")
    mem = Memory(str(Path(tempfile.mkdtemp()) / "forme.db"))

    print("\n  lingua forma-della-fonte |          vago |         cifra | cifra a parole")
    print("  " + "-" * 78)
    esiti: dict[tuple[str, str, str], tuple[str, float | None]] = {}
    for lingua in FONTI:
        for forma, fonte in FONTI[lingua].items():
            celle = []
            for tipo, prop in CLAIM[lingua].items():
                ric = mem.add(prop, topic=f"forme/{lingua}/{forma}", source=fonte, validate="full")
                st, g = str(ric.get("status")), ric.get("grounding_score")
                esiti[(lingua, forma, tipo)] = (st, g)
                celle.append(f"{'AMMESSO' if st != 'quarantined' else 'fermato':>8} {float(g):5.1f}")
            print(f"  {lingua}     {forma:<16} | {celle[0]} | {celle[1]} | {celle[2]}")

    # ── CONTROLLO: la cella gia' nota deve restare com'era.
    print("\nCONTROLLO la cella nota (cifra + fonte «N su M») e' ancora fermata:")
    noti = [esiti[(l, "rapporto", "cifra")] for l in FONTI]
    if any(st != "quarantined" for st, _g in noti):
        print(f"   CADUTO — {noti}: non sto misurando quello che credo")
        return 1
    print(f"   retto — {[f'{g:.1f}' for _s, g in noti]} in {list(FONTI)}")

    # ── ① IL COLPO DI ws3: la forma della fonte cambia il verdetto?
    print("\n① IL COLPO DI ws3 — la mia riga vale oltre il rapporto «N su M»?")
    for tipo in CLAIM["IT"]:
        righe = {
            (l, f): esiti[(l, f, tipo)][0] for l in FONTI for f in FONTI[l]
        }
        distinti = sorted(set(righe.values()))
        stato = "STESSO esito su tutte le forme" if len(distinti) == 1 else "CAMBIA con la forma"
        print(f"   claim {tipo:<15} {stato}: {distinti}")
        if len(distinti) > 1:
            for k, v in righe.items():
                print(f"        {k[0]} {k[1]:<12} {v}")

    # ── ② LA PREDIZIONE DI ws5: il numero a parole elude il layer numerico?
    print("\n② LA PREDIZIONE DI ws5 — «i numeri a parole, mai nel claim»:")
    for lingua in FONTI:
        for forma in FONTI[lingua]:
            c = esiti[(lingua, forma, "cifra")][0]
            p = esiti[(lingua, forma, "cifra a parole")][0]
            if c == "quarantined" and p != "quarantined":
                print(f"   {lingua}/{forma}: CONFERMATA — «3» fermato, «tre» AMMESSO")
            elif c == p:
                print(f"   {lingua}/{forma}: falsificata qui — stesso esito ({c}) per cifra e parola")
            else:
                print(f"   {lingua}/{forma}: rovesciata — cifra {c}, parola {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
