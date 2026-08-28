# -*- coding: utf-8 -*-
"""L'ULTIMO APERTO SULLA FORMA: cosa ha il documento tecnico che il contratto no.

Alle 19:16 ho misurato che sul CONTRATTO la cifra assente e' piatta: fermata a
tutte e otto le lunghezze, ground 0.1-19.3. Il 27/08, sullo stesso tipo di
claim ma su un DOCUMENTO TECNICO, la curva oscillava: 0.3 · 55.2 · 20.8 · 98.2 ·
99.3 · 98.6 · 0.2.

Stessa popolazione (cifra assente), forme opposte. ⇒ resta una sola variabile:
il GENERE del documento. Ma le due misure non condividono nemmeno una
lunghezza — il contratto arrivava a 3516 caratteri, il tecnico partiva da 1000
e arrivava a 14000. Confrontare curve campionate in punti diversi non e' un
confronto.

Qui le due fonti vengono tagliate alle STESSE cinque lunghezze, con un claim
della stessa forma su ciascuna: una cifra che la fonte non contiene, attribuita
a un soggetto che la fonte nomina.

  tecnico    «Il file wake.py conta 9999 LOC.»            (9999 assente)
  contratto  «La cauzione definitiva e' pari a 99999 euro.» (99999 assente)

  se il tecnico oscilla e il contratto no, alle stesse lunghezze
     -> e' il GENERE del documento, e per un prodotto venduto «per contratti e
        referti» e' un dato che riguarda la vetrina, non solo il banco
  se si comportano uguale
     -> la differenza veniva dalle lunghezze diverse, e il 27/08 confrontavo
        curve campionate in punti che non coincidevano

CONTROLLI CHE DEVONO POTER FALLIRE: a ogni lunghezza la cifra del claim NON
deve stare nella fonte, e il soggetto SI'.

Il contratto e' costruito, il documento tecnico e' reale (nel repo).

    python docs/stato-reale/banchi/il-genere-del-documento-cambia-la-curva.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

DOC = Path("docs/archive/2026-05-13_FORGIA.md")

CONTRATTO_BASE = (
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
    "Il committente si riserva la facolta' di verifica in corso d'opera.",
    "Il subappalto e' ammesso nei limiti e con le modalita' previste dalla legge.",
]

LUNGHEZZE = [1000, 2000, 3000, 4000, 6000]

CLAIM_TEC = "Il file wake.py conta 9999 LOC."
CLAIM_CON = "La cauzione definitiva e' pari a 99999 euro."


def _contratto(n: int) -> str:
    pezzi, i = [CONTRATTO_BASE], 0
    while len(" ".join(pezzi)) < n:
        pezzi.append(CLAUSOLE[i % len(CLAUSOLE)])
        i += 1
    return " ".join(pezzi)[:n]


def main() -> int:
    if not DOC.exists():
        print(f"NON RIUSCITO: {DOC} non c'e'")
        return 1
    tecnico_intero = DOC.read_text(encoding="utf-8", errors="replace")

    casi = {}
    for n in LUNGHEZZE:
        t = tecnico_intero[:n]
        c = _contratto(n)
        if "9999" in t or "wake.py" not in t:
            print(f"CONTROLLO CADUTO tecnico a {n}: 9999 presente={'9999' in t}, "
                  f"soggetto presente={'wake.py' in t}")
            return 1
        if "99999" in c or "cauzione" not in c:
            print(f"CONTROLLO CADUTO contratto a {n}: 99999 presente={'99999' in c}, "
                  f"soggetto presente={'cauzione' in c}")
            return 1
        casi[n] = (t, c)
    print(f"  CONTROLLO retto: a tutte e {len(LUNGHEZZE)} le lunghezze la cifra del claim")
    print("  e' assente e il soggetto e' presente, su entrambe le fonti")

    from verimem import client as _client  # noqa: PLC0415
    from verimem.client import Memory  # noqa: PLC0415

    print(f"  codice sotto misura: {_client.__file__}")
    print(f"  tecnico: {DOC} (reale) · contratto: costruito\n")
    mem = Memory(str(Path(tempfile.mkdtemp()) / "genere.db"))

    print(f"  {'lunghezza':>10}   {'TECNICO (reale)':>18}   {'CONTRATTO':>18}")
    print("  " + "-" * 54)
    serie = {"TECNICO": [], "CONTRATTO": []}
    for n, (t, c) in casi.items():
        riga = []
        for nome, fonte, claim in (("TECNICO", t, CLAIM_TEC), ("CONTRATTO", c, CLAIM_CON)):
            ric = mem.add(claim, topic=f"gen/{nome}/{n}", source=fonte, validate="full")
            g = float(ric.get("grounding_score") or -1)
            st = str(ric.get("status"))
            serie[nome].append((st != "quarantined", g))
            riga.append(f"{'ENTRA' if st != 'quarantined' else 'ferma'} {g:6.1f}")
        print(f"  {n:>10}   {riga[0]:>18}   {riga[1]:>18}")

    print("\n  -- LA FORMA, per genere")
    ampiezze = {}
    for nome, s in serie.items():
        stringa = " ".join("E" if e else "." for e, _g in s)
        gs = [g for _e, g in s]
        amp = max(gs) - min(gs)
        ampiezze[nome] = amp
        cambi = sum(1 for i in range(1, len(s)) if s[i][0] != s[i - 1][0])
        print(f"     {nome:<10} {stringa}   ground {min(gs):5.1f}-{max(gs):5.1f}   "
              f"ampiezza {amp:5.1f}   {cambi} cambi di verdetto")

    print()
    at, ac = ampiezze["TECNICO"], ampiezze["CONTRATTO"]
    if at > 40 and ac < 40:
        print("  => E' IL GENERE: alle stesse lunghezze il documento tecnico fa oscillare")
        print("     il punteggio e il contratto no. Per un prodotto venduto «per contratti")
        print("     e referti» il genere della fonte e' una variabile della vetrina.")
    elif at < 40 and ac < 40:
        print("  => NESSUNO dei due oscilla alle stesse lunghezze: la curva del 27/08")
        print("     veniva dalle LUNGHEZZE diverse, e il confronto di allora era fra")
        print("     campionamenti che non coincidevano.")
    else:
        print(f"  => altro caso: ampiezze tecnico {at:.1f}, contratto {ac:.1f}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
