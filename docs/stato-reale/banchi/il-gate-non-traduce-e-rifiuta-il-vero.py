# -*- coding: utf-8 -*-
"""UNDICI FATTI VERI SU DODICI RIFIUTATI — e il sospetto e' la LINGUA.

La batteria del ricalco (fonte fissata, sei fatti veri, due forme ciascuno) ha
dato CITA 1 su 6 e RIFORMULA 0 su 6: il pattern del ricalco era n=1 e cade. Ma
il numero che salta agli occhi e' un altro: **su dodici tentativi il gate
ammette UN fatto vero**.

I fatti sono veri per costruzione — titolo e conteggio letti dal log stesso. Il
sospetto e' nella forma del claim: dice «ha aggiunto N **inserzioni**», e la
fonte dice «N **insertions**(+)». Il claim e' in italiano, la fonte in inglese.

Il banco mette il claim in tre forme, sulla STESSA fonte fissata:

  IT      «Il commit X ha aggiunto N inserzioni.»
  EN      «The commit X added N insertions.»
  LETT    «Il commit X riporta N insertions.»   (italiano, parola inglese)

  se EN passa dove IT no
     -> il gate non attraversa la lingua, e rifiuta fatti veri per questo
  se passano IT ed EN allo stesso modo
     -> la lingua non c'entra e il rifiuto ha un'altra causa
  se LETT passa e IT no
     -> non e' la lingua della FRASE ma la parola del VALORE

CONTROLLO CHE DEVE POTER FALLIRE: i conteggi devono essere univoci nella fonte e
i titoli presenti — altrimenti non sto misurando fatti veri.

Fonte FISSATA su file (`fonte-log-fissata.txt`), committata accanto al banco:
chiunque rilegga misura lo stesso testo.

    python docs/stato-reale/banchi/il-gate-non-traduce-e-rifiuta-il-vero.py
"""

from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path

FONTE_FILE = Path("docs/stato-reale/banchi/fonte-log-fissata.txt")
QUANTI = 5


def main() -> int:
    if not FONTE_FILE.exists():
        print(f"NON RIUSCITO: {FONTE_FILE} non c'e'")
        return 1
    righe = FONTE_FILE.read_text(encoding="utf-8", errors="replace").splitlines()
    log = " ".join(x.strip() for x in righe if x.strip()).replace("@@", "")
    print(f"  fonte FISSATA: {len(log)} caratteri")

    voci, corrente = [], None
    for riga in righe:
        r = riga.strip()
        if r.startswith("@@"):
            _h, _, s = r[2:].partition("|")
            corrente = s
        elif "insertion" in r and corrente:
            m = re.search(r"(\d+) insertion", r)
            if m:
                voci.append((corrente, m.group(1)))
            corrente = None

    buoni = [
        (s, c) for s, c in voci
        if len(re.findall(rf"\b{c}\b", log)) == 1 and 20 < len(s) < 70 and log.find(s[:30]) >= 0
    ]
    if len(buoni) < QUANTI:
        print(f"NON RIUSCITO: fatti buoni {len(buoni)}, ne servono {QUANTI}")
        return 1
    buoni.sort(key=lambda sc: log.find(sc[0][:30]))
    scelti = buoni[:QUANTI]
    print(f"  CONTROLLO retto: {QUANTI} fatti veri con conteggio univoco\n")

    from verimem import client as _client  # noqa: PLC0415
    from verimem.client import Memory  # noqa: PLC0415

    print(f"  codice sotto misura: {_client.__file__}\n")
    mem = Memory(str(Path(tempfile.mkdtemp()) / "lingua.db"))

    FORME = {
        "IT": lambda s, c: f"Il commit «{s}» ha aggiunto {c} inserzioni.",
        "EN": lambda s, c: f"The commit «{s}» added {c} insertions.",
        "LETT": lambda s, c: f"Il commit «{s}» riporta {c} insertions.",
    }

    print(f"  {'ins':>6}   " + "".join(f"{k:>16}" for k in FORME) + "   titolo")
    print("  " + "-" * 78)
    conta = {k: 0 for k in FORME}
    valori = {k: [] for k in FORME}
    for sog, ins in scelti:
        celle = []
        for nome, fabbrica in FORME.items():
            ric = mem.add(fabbrica(sog, ins), topic=f"lg/{nome}/{ins}", source=log, validate="full")
            g = float(ric.get("grounding_score") or -1)
            st = str(ric.get("status"))
            if st != "quarantined":
                conta[nome] += 1
            valori[nome].append(g)
            celle.append(f"{'ENTRA' if st != 'quarantined' else 'ferma'} {g:6.1f}")
        print(f"  {ins:>6}   " + "".join(f"{c:>16}" for c in celle) + f"   {sog[:26]}")

    print()
    for k in FORME:
        v = valori[k]
        print(f"  {k:<5} {conta[k]} su {QUANTI} ammessi   ground {min(v):5.1f}-{max(v):5.1f}")

    print()
    if conta["EN"] > conta["IT"] and conta["EN"] >= QUANTI - 1:
        print("  => E' LA LINGUA: lo stesso fatto vero passa in inglese e viene rifiutato")
        print("     in italiano, sulla stessa fonte. Il gate non attraversa la lingua e")
        print("     rifiuta fatti veri per questo.")
    elif conta["LETT"] > conta["IT"] and conta["EN"] <= conta["IT"]:
        print("  => NON e' la lingua della frase: bastava la parola inglese del VALORE.")
    elif conta["IT"] == conta["EN"] == conta["LETT"]:
        print("  => la lingua non c'entra: le tre forme si comportano uguale, e il")
        print("     rifiuto dei fatti veri ha un'altra causa che non ho isolato.")
    else:
        print(f"  => quadro misto: IT {conta['IT']}, EN {conta['EN']}, LETT {conta['LETT']}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
