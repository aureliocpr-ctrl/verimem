# -*- coding: utf-8 -*-
"""QUANTO CONTORNO BASTA — e un contratto vero quanto ne ha.

Alle 18:44 ho misurato che la coppia «euro grandi» passa da 0/2 fermati (72.1 e
0.9) a 2/2 ammessi (100.0) quando alla fonte si aggiungono 367 caratteri di
altri articoli. E' l'unica coppia che sulla fonte nuda si ferma: percentuali e
date entrano gia' senza contorno.

La domanda che ne discende, e che vale piu' della precedente: **esiste una
quantita' di contorno oltre la quale lo scambio passa e resta passato?** Perche'
un contratto reale non ha 453 caratteri: ne ha decine di migliaia. Se la
protezione svanisce a poche centinaia di caratteri, il numero che conta per chi
scrive la vetrina non e' «il gate ferma questo caso» ma «lo ferma su una fonte
che nessun cliente ha».

Il contorno e' PERTINENTE — altri articoli dello stesso contratto, senza le
cifre in gioco — perche' il 26/08 avevo gia' escluso che la natura del contorno
predica l'esito, e perche' un contorno artificiale non e' cio' che un documento
vero porta con se'.

⚠️ Il 27/08 la stessa superficie si era mostrata NON MONOTONA (0.3 → 55.2 →
20.8 → 98.2 → 99.3 → 0.2 al crescere della fonte). Quindi il banco non cerca
«la soglia»: cerca la FORMA, e se oscilla lo dice.

CONTROLLI CHE DEVONO POTER FALLIRE:
  a) il claim VERO resta ammesso a ogni lunghezza (altrimenti il contorno sta
     rompendo la fonte, non spostando il giudizio);
  b) le cifre in gioco (148000, 22000) NON devono comparire nel contorno.

Fonte costruita nella forma del dominio, dichiarata.

    python docs/stato-reale/banchi/quanto-contorno-basta-perche-lo-scambio-passi.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

BASE = (
    "Art. 3 - La penale per il ritardo nella consegna e' pari al 2% dell'importo "
    "contrattuale per ogni settimana di ritardo. "
    "Art. 4 - La penale per difformita' qualitativa e' pari al 7% dell'importo "
    "contrattuale. "
    "Art. 5 - Il termine di consegna e' fissato al 12 marzo 2027. "
    "Art. 6 - Il termine per la contestazione dei vizi e' fissato al 30 aprile 2027. "
    "Art. 7 - L'importo contrattuale e' di 148000 euro. "
    "Art. 8 - La cauzione definitiva e' pari a 22000 euro."
)

# Clausole di stile, pertinenti e prive di cifre: e' quello che un contratto
# vero porta con se' fra una clausola numerica e l'altra.
CLAUSOLE = [
    "Le parti danno atto di aver preso visione integrale del presente accordo.",
    "Il foro competente per ogni controversia e' quello della sede legale del committente.",
    "Le comunicazioni fra le parti avvengono a mezzo di posta elettronica certificata.",
    "Il presente atto e' redatto in duplice originale, uno per ciascuna delle parti.",
    "L'appaltatore dichiara di essere in regola con gli obblighi contributivi.",
    "La cessione del contratto a terzi e' subordinata al consenso scritto del committente.",
    "Il committente si riserva la facolta' di verifica in corso d'opera.",
    "Le modifiche al presente accordo sono valide solo se pattuite per iscritto.",
    "L'appaltatore garantisce la conformita' delle lavorazioni alle norme tecniche vigenti.",
    "Il subappalto e' ammesso nei limiti e con le modalita' previste dalla legge.",
]

AGGIUNTE = [0, 100, 200, 400, 800, 1600, 3200, 6400]

SCAMBIO_A = "La cauzione definitiva e' pari a 148000 euro."
SCAMBIO_B = "L'importo contrattuale e' di 22000 euro."
VERO = "L'importo contrattuale e' di 148000 euro."


def _fonte(extra: int) -> str:
    if extra <= 0:
        return BASE
    coda, i = [], 0
    while sum(len(c) + 1 for c in coda) < extra:
        coda.append(CLAUSOLE[i % len(CLAUSOLE)])
        i += 1
    return BASE + " " + " ".join(coda)


def main() -> int:
    fonti = {}
    for n in AGGIUNTE:
        f = _fonte(n)
        coda = f[len(BASE):]
        if "148000" in coda or "22000" in coda:
            print(f"CONTROLLO CADUTO a +{n}: una cifra in gioco e' finita nel contorno")
            return 1
        fonti[n] = f
    print(f"  CONTROLLO retto: nessuna cifra in gioco nel contorno, {len(AGGIUNTE)} fonti")
    print(f"  base {len(BASE)} caratteri, la piu' lunga {len(fonti[AGGIUNTE[-1]])}")

    from verimem import client as _client  # noqa: PLC0415
    from verimem.client import Memory  # noqa: PLC0415

    print(f"  codice sotto misura: {_client.__file__}\n")
    mem = Memory(str(Path(tempfile.mkdtemp()) / "quanto.db"))

    print(f"  {'fonte':>7}  {'VERO':>14}   {'cauzione=148000':>16}   {'importo=22000':>15}")
    print("  " + "-" * 62)
    righe = []
    for n, fonte in fonti.items():
        out = []
        for prop in (VERO, SCAMBIO_A, SCAMBIO_B):
            ric = mem.add(prop, topic=f"qc/{n}/{len(out)}", source=fonte, validate="full")
            g = float(ric.get("grounding_score") or -1)
            st = str(ric.get("status"))
            out.append((st, g))
        righe.append((len(fonte), out))
        def cella(x):
            st, g = x
            return f"{'OK' if st != 'quarantined' else 'ferm'} {g:6.1f}"
        print(f"  {len(fonte):>7}  {cella(out[0]):>14}   {cella(out[1]):>16}   {cella(out[2]):>15}")

    print("\nCONTROLLO il claim VERO resta ammesso a ogni lunghezza:")
    male = [c for c, out in righe if out[0][0] == "quarantined"]
    if male:
        print(f"   CADUTO — quarantinato alle lunghezze {male}: il contorno rompe la fonte")
        return 1
    print(f"   retto — ammesso su tutte e {len(righe)} le lunghezze")

    print("\n  -- LA FORMA")
    for idx, nome in ((1, "cauzione=148000"), (2, "importo=22000")):
        serie = [(c, out[idx][0] != "quarantined", out[idx][1]) for c, out in righe]
        stringa = " ".join("E" if e else "." for _c, e, _g in serie)
        entrati = sum(1 for _c, e, _g in serie if e)
        print(f"     {nome:<16} {stringa}    ({entrati} su {len(serie)} entrano)")
        # dove cambia
        cambi = [
            (serie[i - 1][0], serie[i][0], serie[i - 1][1], serie[i][1])
            for i in range(1, len(serie))
            if serie[i][1] != serie[i - 1][1]
        ]
        for a, b, ea, eb in cambi:
            verso = "ferma -> ENTRA" if eb else "ENTRA -> ferma"
            print(f"        fra {a} e {b} caratteri: {verso}")
        if len(cambi) > 1:
            print("        piu' di un cambio: NON c'e' una soglia, la forma oscilla")
        elif len(cambi) == 1 and cambi[0][3]:
            print("        un solo cambio, e in avanti: la protezione svanisce e non torna")
    return 0


if __name__ == "__main__":
    sys.exit(main())
