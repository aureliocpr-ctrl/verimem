# -*- coding: utf-8 -*-
"""L'APERTO DELLE 19:07: la curva oscillante veniva dal claim o dalla fonte?

Nessuna delle due, e la risposta era gia' nei dati.

Il 27/08 la curva oscillava (0.3 · 55.2 · 20.8 · 98.2 · 99.3 · 98.6 · 0.2) su un
claim che citava una cifra ASSENTE dal documento («wake.py conta 9999 LOC»).
Oggi la curva e' monotona su uno SCAMBIO DI ATTRIBUZIONE, dove la cifra nella
fonte c'e' ed e' solo riferita a un'altra cosa («la cauzione e' 148000 euro»,
mentre 148000 e' l'importo contrattuale).

@ws3 le ha gia' separate come due popolazioni: cifra ASSENTE -> decide `L4.1`
(9 su 10 nella mia batteria); cifra PRESENTE mal attribuita -> `L4.1` non
compare mai (0 su 12) e decide il solo giudice. ⇒ se le due popolazioni hanno
due DECISORI diversi, non c'e' ragione perche' abbiano la stessa forma.

Il test tiene fissa la fonte e muove SOLO la popolazione. Stessa base, stesse
lunghezze di contorno, due claim gemelli sullo stesso soggetto:

  ASSENTE   «La cauzione definitiva e' pari a 99999 euro.»   (99999 non c'e')
  SCAMBIO   «La cauzione definitiva e' pari a 148000 euro.»  (148000 e' l'importo)

  se ASSENTE oscilla e SCAMBIO no -> e' la POPOLAZIONE, e l'aperto e' chiuso
  se si comportano uguale        -> la differenza del 27/08 sta altrove, e la
                                    congettura va detta caduta

CONTROLLI CHE DEVONO POTER FALLIRE: «99999» non deve stare nella fonte a nessuna
lunghezza, «148000» deve starci sempre, e il claim VERO resta ammesso.

Fonte costruita, dichiarata.

    python docs/stato-reale/banchi/due-popolazioni-due-forme.py
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

CLAUSOLE = [
    "Le parti danno atto di aver preso visione integrale del presente accordo.",
    "Il foro competente per ogni controversia e' quello della sede del committente.",
    "Le comunicazioni fra le parti avvengono a mezzo di posta elettronica certificata.",
    "Il presente atto e' redatto in duplice originale, uno per ciascuna parte.",
    "L'appaltatore dichiara di essere in regola con gli obblighi contributivi.",
    "Le modifiche al presente accordo sono valide solo se pattuite per iscritto.",
]

LUNGHEZZE = [0, 100, 160, 300, 500, 900, 1600, 3000]

ASSENTE = "La cauzione definitiva e' pari a 99999 euro."
SCAMBIO = "La cauzione definitiva e' pari a 148000 euro."
VERO = "La cauzione definitiva e' pari a 22000 euro."


def _fonte(extra: int) -> str:
    if extra <= 0:
        return BASE
    pezzi, i = [], 0
    while sum(len(p) + 1 for p in pezzi) < extra:
        pezzi.append(CLAUSOLE[i % len(CLAUSOLE)])
        i += 1
    return BASE + " " + " ".join(pezzi)


def main() -> int:
    fonti = {}
    for n in LUNGHEZZE:
        f = _fonte(n)
        if "99999" in f:
            print(f"CONTROLLO CADUTO a +{n}: 99999 e' finito nella fonte")
            return 1
        if "148000" not in f:
            print(f"CONTROLLO CADUTO a +{n}: 148000 non e' nella fonte")
            return 1
        fonti[n] = f
    print(f"  CONTROLLO retto: 99999 assente e 148000 presente in tutte le {len(LUNGHEZZE)} fonti")

    from verimem import client as _client  # noqa: PLC0415
    from verimem.client import Memory  # noqa: PLC0415

    print(f"  codice sotto misura: {_client.__file__}")
    print(f"  base {len(BASE)} caratteri, la piu' lunga {len(fonti[LUNGHEZZE[-1]])}\n")
    mem = Memory(str(Path(tempfile.mkdtemp()) / "pop.db"))

    print(f"  {'fonte':>7}   {'ASSENTE (99999)':>18}   {'SCAMBIO (148000)':>18}")
    print("  " + "-" * 52)
    serie = {"ASSENTE": [], "SCAMBIO": []}
    for n, fonte in fonti.items():
        riga = []
        for nome, prop in (("ASSENTE", ASSENTE), ("SCAMBIO", SCAMBIO)):
            ric = mem.add(prop, topic=f"pop/{nome}/{n}", source=fonte, validate="full")
            g = float(ric.get("grounding_score") or -1)
            st = str(ric.get("status"))
            serie[nome].append((st != "quarantined", g))
            riga.append(f"{'ENTRA' if st != 'quarantined' else 'ferma'} {g:6.1f}")
        print(f"  {len(fonte):>7}   {riga[0]:>18}   {riga[1]:>18}")

    print("\nCONTROLLO il claim VERO e' ammesso sulla fonte piu' lunga:")
    ric = mem.add(VERO, topic="pop/vero", source=fonti[LUNGHEZZE[-1]], validate="full")
    if str(ric.get("status")) == "quarantined":
        print(f"   CADUTO — quarantinato ({float(ric.get('grounding_score') or -1):.1f})")
        return 1
    print(f"   retto — ammesso, ground {float(ric.get('grounding_score') or -1):.1f}\n")

    print("  -- LA FORMA, per popolazione")
    forme = {}
    for nome, s in serie.items():
        stringa = " ".join("E" if e else "." for e, _g in s)
        cambi = sum(1 for i in range(1, len(s)) if s[i][0] != s[i - 1][0])
        forme[nome] = cambi
        etichetta = "monotona" if cambi <= 1 else f"OSCILLA ({cambi} cambi)"
        gs = [g for _e, g in s]
        print(f"     {nome:<9} {stringa}    {etichetta}   ground {min(gs):.1f}-{max(gs):.1f}")

    print()
    if forme["ASSENTE"] > 1 and forme["SCAMBIO"] <= 1:
        print("  => E' LA POPOLAZIONE: la cifra assente oscilla, lo scambio no.")
        print("     Due decisori diversi, due forme diverse. L'aperto delle 19:07 e' chiuso.")
    elif forme["ASSENTE"] <= 1 and forme["SCAMBIO"] <= 1:
        print("  => CADE: sulla stessa fonte non oscilla nessuna delle due. La curva")
        print("     del 27/08 dipendeva dalla FONTE (documento tecnico) e non dal claim.")
    else:
        print(f"  => altro caso: ASSENTE {forme['ASSENTE']} cambi, SCAMBIO {forme['SCAMBIO']}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
