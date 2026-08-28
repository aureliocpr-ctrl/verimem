# -*- coding: utf-8 -*-
"""LE STESSE COPPIE SU DUE FONTI: e' l'unita' o e' quello che c'e' intorno?

Il banco `e-l-unita-o-l-ordine-di-grandezza.py` ha dato 10 scambi ammessi su 12,
e fra questi gli EURO GRANDI 2 su 2 — che nel candidato di @ws3 e nella mia
misura del 27/08 erano 0 su 2, fermati a 4.9 e 0.9.

Fra le due misure e' cambiata la FONTE: 453 caratteri e 6 articoli il 27/08,
789 caratteri e 12 articoli oggi. ⇒ la spiegazione «l'unita' euro e' robusta»
e quella «conta quanto testo c'e' intorno» predicono cose diverse, e il 27/08
alle 22:15 avevo gia' misurato che il contorno ribalta gli scambi fermati.

Questo banco tiene le COPPIE identiche e muove SOLO la fonte:

  NUDA    i sei articoli del 27/08, 453 caratteri
  RICCA   i dodici articoli di oggi, 789 caratteri

Le coppie sono le stesse in entrambe: percentuali (2% e 7%) ed euro grandi
(148000 e 22000). Le altre due coppie della fonte ricca non esistono in quella
nuda e restano fuori: aggiungerle cambierebbe due cose insieme.

  se gli euro grandi si fermano sulla NUDA e entrano sulla RICCA
     -> non e' l'unita', e' il contorno, e il candidato di ws3 cambia bersaglio
  se si comportano uguale sulle due
     -> l'unita' regge e la differenza di ieri viene da altro

CONTROLLO CHE DEVE POTER FALLIRE: le cifre delle coppie devono stare in
ENTRAMBE le fonti, e i claim VERI devono essere ammessi su entrambe.

    python docs/stato-reale/banchi/non-e-l-unita-e-la-fonte-intorno.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

NUDA = (
    "Art. 3 - La penale per il ritardo nella consegna e' pari al 2% dell'importo "
    "contrattuale per ogni settimana di ritardo. "
    "Art. 4 - La penale per difformita' qualitativa e' pari al 7% dell'importo "
    "contrattuale. "
    "Art. 5 - Il termine di consegna e' fissato al 12 marzo 2027. "
    "Art. 6 - Il termine per la contestazione dei vizi e' fissato al 30 aprile 2027. "
    "Art. 7 - L'importo contrattuale e' di 148000 euro. "
    "Art. 8 - La cauzione definitiva e' pari a 22000 euro."
)

RICCA = NUDA + (
    " Art. 9 - L'acconto alla stipula e' pari al 34% del corrispettivo. "
    "Art. 11 - Il saldo alla consegna e' pari al 61% del corrispettivo. "
    "Art. 13 - I diritti di segreteria ammontano a 16 euro. "
    "Art. 15 - Le spese di registrazione ammontano a 50 euro. "
    "Art. 17 - Il preavviso per il recesso e' di 8 giorni. "
    "Art. 19 - Il termine per la contestazione dei vizi e' di 45 giorni."
)

COPPIE = [
    ("percentuali 2/7",
     "La penale per il ritardo e' pari al 7% dell'importo contrattuale.",
     "La penale per difformita' qualitativa e' pari al 2% dell'importo contrattuale.",
     ("7%", "2%")),
    ("euro grandi",
     "La cauzione definitiva e' pari a 148000 euro.",
     "L'importo contrattuale e' di 22000 euro.",
     ("148000", "22000")),
    ("date",
     "Il termine di consegna e' fissato al 30 aprile 2027.",
     "Il termine per la contestazione dei vizi e' fissato al 12 marzo 2027.",
     ("30 aprile", "12 marzo")),
]

VERI = [
    "La penale per il ritardo e' pari al 2% dell'importo contrattuale.",
    "L'importo contrattuale e' di 148000 euro.",
]

FONTI = {"NUDA": NUDA, "RICCA": RICCA}


def main() -> int:
    for nome, fonte in FONTI.items():
        for etichetta, _a, _b, cifre in COPPIE:
            for c in cifre:
                if c not in fonte:
                    print(f"CONTROLLO CADUTO: {c!r} non e' nella fonte {nome} ({etichetta})")
                    return 1
    print("  CONTROLLO retto: le cifre di tutte le coppie stanno in entrambe le fonti")
    print(f"  NUDA {len(NUDA)} caratteri · RICCA {len(RICCA)} caratteri "
          f"(+{len(RICCA) - len(NUDA)} di contorno pertinente)\n")

    from verimem.client import Memory  # noqa: PLC0415

    mem = Memory(str(Path(tempfile.mkdtemp()) / "ab.db"))

    for nome, fonte in FONTI.items():
        for i, prop in enumerate(VERI):
            r = mem.add(prop, topic=f"ab/vero/{nome}/{i}", source=fonte, validate="full")
            if str(r.get("status")) == "quarantined":
                g = float(r.get("grounding_score") or -1)
                print(f"CONTROLLO CADUTO: il vero {prop!r} e' quarantinato su {nome} ({g:.1f})")
                return 1
    print("  CONTROLLO retto: i claim VERI sono ammessi su entrambe le fonti\n")

    print(f"  {'coppia':<18} {'fonte':<7} {'verso A':>15}   {'verso B':>15}")
    print("  " + "-" * 62)
    tab = {}
    for i, (etichetta, a, b, _c) in enumerate(COPPIE):
        for nome, fonte in FONTI.items():
            out = []
            for j, prop in enumerate((a, b)):
                ric = mem.add(prop, topic=f"ab/{i}/{nome}/{j}", source=fonte, validate="full")
                sc = float(ric.get("grounding_score") or -1)
                st = str(ric.get("status"))
                out.append((st, sc))
            (sa, ga), (sb, gb) = out
            ea = "ENTRA" if sa != "quarantined" else "ferma"
            eb = "ENTRA" if sb != "quarantined" else "ferma"
            tab[(etichetta, nome)] = (ea, ga, eb, gb)
            print(f"  {etichetta:<18} {nome:<7} {ea:>8} {ga:6.1f}   {eb:>8} {gb:6.1f}")
        print()

    print("  -- IL DISCRIMINANTE")
    cambiati = []
    for etichetta, _a, _b, _c in COPPIE:
        n = tab[(etichetta, "NUDA")]
        r = tab[(etichetta, "RICCA")]
        entra_n = sum(1 for x in (n[0], n[2]) if x == "ENTRA")
        entra_r = sum(1 for x in (r[0], r[2]) if x == "ENTRA")
        segno = "  <-- CAMBIA" if entra_n != entra_r else ""
        print(f"     {etichetta:<18} nuda {entra_n}/2   ricca {entra_r}/2{segno}")
        if entra_n != entra_r:
            cambiati.append((etichetta, entra_n, entra_r))

    if cambiati:
        print("\n  => NON e' l'unita': le stesse coppie cambiano esito quando cambia")
        print("     SOLO cio' che c'e' intorno nella fonte. Il candidato di ws3")
        print("     misura il contorno delle sue fonti, non la fragilita' dell'unita'.")
    else:
        print("\n  => le coppie si comportano uguale sulle due fonti: il contorno non")
        print("     spiega la differenza, e la va cercata altrove.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
