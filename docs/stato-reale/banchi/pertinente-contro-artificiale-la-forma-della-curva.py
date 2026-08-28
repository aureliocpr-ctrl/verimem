# -*- coding: utf-8 -*-
"""LA NATURA DEL CONTORNO DECIDE LA FORMA DELLA CURVA? Il test che mancava.

Alle 19:00 ho pubblicato un'osservazione dichiarandola NON un risultato: col
contorno PERTINENTE la curva e' monotona (la protezione svanisce a 613 caratteri
e non torna), mentre col contorno ARTIFICIALE del 27/08 la stessa superficie
oscillava (0.3 · 55.2 · 20.8 · 98.2 · 99.3 · 0.2). Ma quella misura aveva un
claim diverso e una fonte diversa, quindi non era un A/B fra i due contorni.

Qui lo e': stesso claim, stessa fonte base, stesse lunghezze, e QUATTRO nature
di coda. Le tre artificiali sono quelle gia' usate nel dossier ⑩, dove erano
state scelte per coprire generi diversi.

  pertinente     clausole di stile dello stesso contratto, senza cifre
  prosa estranea un testo che con il contratto non c'entra niente
  pseudo-parole  parole inventate, morfologia italiana, nessun significato
  numeri         cifre sparse senza sintassi

  se il PERTINENTE e' monotono e gli ARTIFICIALI oscillano
     -> la natura del contorno decide la forma, e l'osservazione diventa un dato
  se oscillano tutti o nessuno
     -> la differenza del 27/08 veniva dal claim o dalla fonte, non dal contorno,
        e l'osservazione va ritirata

⚠️ Il 26/08 avevo escluso che la natura del contorno predica l'ESITO su una
lunghezza singola (numeri 99.9 · pseudo-parole 99.3 · prosa IT 98.4 · prosa EN
25.2). Qui la domanda e' diversa: non l'esito su un punto, ma la FORMA su otto.
Una variabile puo' non spostare un punto e governare una curva.

CONTROLLI CHE DEVONO POTER FALLIRE: il claim VERO resta ammesso ovunque, e le
cifre in gioco non compaiono in nessuna coda.

Fonte costruita, dichiarata.

    python docs/stato-reale/banchi/pertinente-contro-artificiale-la-forma-della-curva.py
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

PEZZI = {
    "pertinente": [
        "Le parti danno atto di aver preso visione integrale del presente accordo.",
        "Il foro competente per ogni controversia e' quello della sede del committente.",
        "Le comunicazioni fra le parti avvengono a mezzo di posta elettronica certificata.",
        "Il presente atto e' redatto in duplice originale, uno per ciascuna parte.",
        "L'appaltatore dichiara di essere in regola con gli obblighi contributivi.",
        "Le modifiche al presente accordo sono valide solo se pattuite per iscritto.",
    ],
    "prosa estranea": [
        "La fioritura dei ciliegi anticipa di qualche giorno quando l'inverno e' mite.",
        "Nel golfo il vento di maestrale si alza quasi sempre nel primo pomeriggio.",
        "La ricetta tradizionale prevede una lunga lievitazione a temperatura ambiente.",
        "I gabbiani seguono i pescherecci fino all'imboccatura del porto.",
        "La biblioteca comunale conserva un fondo di stampe ottocentesche.",
        "Il sentiero costeggia il torrente fino al ponte di pietra.",
    ],
    "pseudo-parole": [
        "Larvi turnesco pilanto verduschi mendrale.",
        "Morbanto celitre pasguno velardi troncabo.",
        "Tirvassi mendulo craspite zonarto belfusco.",
        "Raminte dolvaggio scurbeno taltrino gavesi.",
        "Pindolo marvesco lutranio cerpasso vindale.",
        "Ostrivo naldescо puribante teschialo mardu.",
    ],
    "numeri": [
        "731 904 268 415 597 130 842 076 359 681.",
        "224 950 173 608 447 512 369 785 041 926.",
        "638 271 095 483 716 250 894 037 561 128.",
        "417 302 869 154 723 690 285 431 907 546.",
        "952 186 743 025 619 378 460 217 583 094.",
        "306 574 821 963 140 758 692 315 047 289.",
    ],
}

LUNGHEZZE = [0, 160, 400, 900, 1800, 3600]

SCAMBIO = "La cauzione definitiva e' pari a 148000 euro."
VERO = "L'importo contrattuale e' di 148000 euro."


def _coda(natura: str, extra: int) -> str:
    if extra <= 0:
        return ""
    pezzi, i = [], 0
    while sum(len(p) + 1 for p in pezzi) < extra:
        pezzi.append(PEZZI[natura][i % len(PEZZI[natura])])
        i += 1
    return " " + " ".join(pezzi)


def main() -> int:
    for natura in PEZZI:
        for n in LUNGHEZZE:
            coda = _coda(natura, n)
            if "148000" in coda or "22000" in coda:
                print(f"CONTROLLO CADUTO: una cifra in gioco e' nella coda {natura} a +{n}")
                return 1
    print(f"  CONTROLLO retto: nessuna cifra in gioco nelle {len(PEZZI) * len(LUNGHEZZE)} code")

    from verimem import client as _client  # noqa: PLC0415
    from verimem.client import Memory  # noqa: PLC0415

    print(f"  codice sotto misura: {_client.__file__}")
    print(f"  base {len(BASE)} caratteri, claim: {SCAMBIO!r}\n")
    mem = Memory(str(Path(tempfile.mkdtemp()) / "forma.db"))

    intest = "  " + f"{'natura':<16}" + "".join(f"{n:>10}" for n in LUNGHEZZE)
    print(intest)
    print("  " + "-" * (len(intest) - 2))
    curve = {}
    for natura in PEZZI:
        riga, serie = [], []
        for n in LUNGHEZZE:
            fonte = BASE + _coda(natura, n)
            ric = mem.add(SCAMBIO, topic=f"fc/{natura}/{n}", source=fonte, validate="full")
            g = float(ric.get("grounding_score") or -1)
            st = str(ric.get("status"))
            serie.append((st != "quarantined", g))
            riga.append(f"{'E' if st != 'quarantined' else '.'}{g:9.1f}")
        curve[natura] = serie
        print(f"  {natura:<16}" + "".join(f"{c:>10}" for c in riga))

    print("\nCONTROLLO il claim VERO resta ammesso, sulla coda piu' lunga di ogni natura:")
    for natura in PEZZI:
        fonte = BASE + _coda(natura, LUNGHEZZE[-1])
        ric = mem.add(VERO, topic=f"fc/vero/{natura}", source=fonte, validate="full")
        if str(ric.get("status")) == "quarantined":
            g = float(ric.get("grounding_score") or -1)
            print(f"   CADUTO — il VERO e' quarantinato con {natura} ({g:.1f})")
            return 1
    print(f"   retto — ammesso con tutte e {len(PEZZI)} le nature\n")

    print("  -- LA FORMA, per natura")
    for natura, serie in curve.items():
        stringa = " ".join("E" if e else "." for e, _g in serie)
        cambi = sum(1 for i in range(1, len(serie)) if serie[i][0] != serie[i - 1][0])
        forma = ("monotona" if cambi <= 1 else f"OSCILLA ({cambi} cambi)")
        print(f"     {natura:<16} {stringa}    {forma}")

    monotone = [n for n, s in curve.items()
                if sum(1 for i in range(1, len(s)) if s[i][0] != s[i - 1][0]) <= 1]
    oscillanti = [n for n in curve if n not in monotone]
    print()
    if "pertinente" in monotone and oscillanti and set(oscillanti) == set(PEZZI) - {"pertinente"}:
        print("  => CONFERMATA: il pertinente e' monotono e tutti gli artificiali oscillano.")
        print("     La natura del contorno non sposta un punto (misurato il 26/08) ma")
        print("     governa la FORMA della curva.")
    elif not oscillanti:
        print("  => RITIRATA: oscilla nessuno. La differenza del 27/08 veniva dal claim")
        print("     o dalla fonte, non dalla natura del contorno.")
    else:
        print(f"  => parziale: monotone {monotone}, oscillanti {oscillanti}.")
        print("     Non basta a sostenere l'osservazione come l'avevo scritta.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
