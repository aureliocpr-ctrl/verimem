# -*- coding: utf-8 -*-
"""LA CONGETTURA DELLE 22:07, messa alla prova: uno o due fenomeni?

Alle 22:07 ho scritto che lo scambio di attribuzione ASSOMIGLIA al contorno del
dossier ⑩ — non monotono, spiegazioni che cadono una dopo l'altra (la' sei,
qui quattro) — e ho dichiarato che «siano lo stesso fenomeno e' una congettura,
non un risultato».

Si mette alla prova cosi': prendo gli scambi che il gate FERMA e ci aggiungo il
contorno. Se il contorno li fa salire, i due fenomeni INTERAGISCONO e la
superficie e' una sola; se restano fermi con qualunque contorno, sono due cose
diverse e la congettura cade.

  scambio FERMATO   «La cauzione definitiva e' pari a 148000 euro»     ground 4.9
  scambio FERMATO   «L'importo contrattuale e' di 22000 euro»          ground 0.9

Le nature del contorno sono quelle gia' misurate nel dossier ⑩ (numeri 99.9 ·
pseudo-parole 99.3 · prosa IT 98.4 · prosa EN 25.2), riusate qui perche' li'
erano state scelte per coprire generi diversi.

CONTROLLO CHE DEVE POTER FALLIRE: il claim VERO deve restare ammesso con OGNI
contorno. Se il contorno abbatte anche il vero, non sto misurando un
ribaltamento: sto rompendo la fonte.

⚠️ Fonte costruita, come nei due banchi precedenti, e dichiarata.

    python docs/stato-reale/banchi/il-contorno-ribalta-anche-lo-scambio.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

CONTRATTO = (
    "Art. 3 - La penale per il ritardo nella consegna e' pari al 2% dell'importo "
    "contrattuale per ogni settimana di ritardo. "
    "Art. 4 - La penale per difformita' qualitativa e' pari al 5% dell'importo "
    "contrattuale. "
    "Art. 5 - Il termine di consegna e' fissato al 12 marzo 2027. "
    "Art. 6 - Il termine per la contestazione dei vizi e' fissato al 30 aprile 2027. "
    "Art. 7 - L'importo contrattuale e' di 148000 euro. "
    "Art. 8 - La cauzione definitiva e' pari a 22000 euro."
)

CONTORNI = {
    "nessuno": "",
    "prosa IT": (
        " Le parti danno atto di aver letto integralmente il presente accordo. "
        "La sede di stipula e' presso gli uffici indicati in epigrafe. "
        "Il presente atto e' redatto in duplice originale. "
        "Le comunicazioni avvengono per posta elettronica certificata."
    ),
    "numeri": " 731 904 268 415 597 130 842 076 359 681 224 950 173 608 447 " * 2,
    "pseudo-parole": (
        " Larvi turnesco pilanto verduschi. Morbanto celitre pasguno velardi. "
        "Tirvassi mendulo craspite zonarto. Belfusco raminte dolvaggio."
    ),
}

VERO = "La cauzione definitiva e' pari a 22000 euro."
SCAMBI = [
    "La cauzione definitiva e' pari a 148000 euro.",
    "L'importo contrattuale e' di 22000 euro.",
]


def main() -> int:
    from verimem.client import Memory  # noqa: PLC0415

    mem = Memory(str(Path(tempfile.mkdtemp()) / "unif.db"))

    print(f"  {'contorno':<16} {'car.':>6}   {'VERO':>12}   {'cauzione=148000':>16}   {'importo=22000':>14}")
    print("  " + "-" * 78)
    tabella = {}
    for nome, coda in CONTORNI.items():
        fonte = CONTRATTO + coda
        riga = []
        for prop in [VERO] + SCAMBI:
            ric = mem.add(prop, topic=f"unif/{nome}/{len(riga)}", source=fonte, validate="full")
            g = float(ric.get("grounding_score") or -1)
            st = str(ric.get("status"))
            riga.append((st, g))
        tabella[nome] = riga
        def f(x):
            st, g = x
            return f"{'OK' if st != 'quarantined' else 'ferm'} {g:6.1f}"
        print(f"  {nome:<16} {len(fonte):>6}   {f(riga[0]):>12}   {f(riga[1]):>16}   {f(riga[2]):>14}")

    print("\nCONTROLLO il claim VERO resta ammesso con ogni contorno:")
    male = [n for n, r in tabella.items() if r[0][0] == "quarantined"]
    if male:
        print(f"   CADUTO — il vero e' quarantinato con {male}: il contorno rompe la fonte")
        return 1
    print(f"   retto — ammesso con tutti e {len(CONTORNI)} i contorni")

    print("\nLA CONGETTURA — il contorno ribalta anche gli scambi fermati?")
    base = tabella["nessuno"]
    ribaltati = []
    for i, nome_claim in enumerate(("cauzione=148000", "importo=22000"), start=1):
        g0 = base[i][1]
        print(f"   {nome_claim}: senza contorno {g0:.1f}")
        for nome, r in tabella.items():
            if nome == "nessuno":
                continue
            st, g = r[i]
            segno = "  ← RIBALTA" if st != "quarantined" else ""
            print(f"      con {nome:<16} {g:6.1f}  {st}{segno}")
            if st != "quarantined":
                ribaltati.append((nome_claim, nome, g))

    if ribaltati:
        print("\n  ⇒ INTERAGISCONO: uno scambio che il gate ferma entra appena la fonte")
        print("    porta del contorno. I due fronti sono la stessa superficie, e una")
        print("    cura che ne prende uno solo lascia aperto l'altro.")
    else:
        print("\n  ⇒ LA CONGETTURA CADE: gli scambi fermati restano fermati con tutti i")
        print("    contorni provati. Sono due fenomeni distinti, e vanno curati a parte.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
