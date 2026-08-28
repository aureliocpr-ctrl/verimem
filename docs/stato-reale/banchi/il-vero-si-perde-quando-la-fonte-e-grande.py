# -*- coding: utf-8 -*-
"""TREDICI FATTI VERI RIFIUTATI SU QUINDICI: e' la DILUIZIONE?

Due sospetti caduti nell'ordine, entrambi miei:
  · il RICALCO (il claim passa solo citando il titolo) -> batteria: CITA 1 su 6;
  · la LINGUA (claim italiano su fonte inglese) -> IT 1/5, EN 0/5, LETT 1/5.

Resta il numero: su una fonte reale fissata di 38387 caratteri, il gate ammette
2 fatti VERI su 15 tentativi. E resta un'ultima variabile ovvia che non ho
ancora tolto: **quanto e' grande la fonte in cui il fatto sta**. Una riga
«1 file changed, 148 insertions(+)» dentro 38387 caratteri e' lo 0,1% del testo.

Il banco prende gli STESSI fatti veri e li misura su fonti di taglia crescente,
tutte ritagliate dalla stessa fonte fissata e tutte CONTENENTI il fatto:

  minima   il titolo del commit e la sua riga di conteggio, nient'altro
  media    la finestra di 2000 caratteri intorno al fatto
  larga    la finestra di 8000 caratteri intorno al fatto
  intera   la fonte fissata, 38387 caratteri

  se i fatti passano sulla minima e cadono sull'intera
     -> il gate perde i fatti VERI quando la fonte e' grande, ed e' un falso
        negativo per diluizione, misurato su fonte reale
  se cadono anche sulla minima
     -> non e' la taglia, e il rifiuto ha una causa che non ho ancora toccato

CONTROLLO CHE DEVE POTER FALLIRE: ogni fonte, a ogni taglia, deve contenere il
titolo e il conteggio del fatto che si sta misurando.

Fonte FISSATA su file, committata accanto al banco.

    python docs/stato-reale/banchi/il-vero-si-perde-quando-la-fonte-e-grande.py
"""

from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path

FONTE_FILE = Path("docs/stato-reale/banchi/fonte-log-fissata.txt")
QUANTI = 4


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
                voci.append((corrente, m.group(1), r.strip()))
            corrente = None

    buoni = [
        (s, c, r) for s, c, r in voci
        if len(re.findall(rf"\b{c}\b", log)) == 1 and 20 < len(s) < 70 and log.find(s[:30]) >= 0
    ]
    if len(buoni) < QUANTI:
        print(f"NON RIUSCITO: fatti buoni {len(buoni)}, ne servono {QUANTI}")
        return 1
    buoni.sort(key=lambda x: log.find(x[0][:30]))
    scelti = buoni[:QUANTI]

    from verimem import client as _client  # noqa: PLC0415
    from verimem.client import Memory  # noqa: PLC0415

    print(f"  codice sotto misura: {_client.__file__}\n")
    mem = Memory(str(Path(tempfile.mkdtemp()) / "dil.db"))

    print(f"  {'ins':>6}   {'minima':>15}{'media 2k':>15}{'larga 8k':>15}{'intera 38k':>15}")
    print("  " + "-" * 74)
    conta = {"minima": 0, "media": 0, "larga": 0, "intera": 0}
    for sog, ins, riga_conteggio in scelti:
        pos = log.find(sog[:30])
        fonti = {
            "minima": f"{sog} {riga_conteggio}",
            "media": log[max(0, pos - 1000): pos + 1000],
            "larga": log[max(0, pos - 4000): pos + 4000],
            "intera": log,
        }
        celle = []
        for nome, fonte in fonti.items():
            if sog[:30] not in fonte or ins not in fonte:
                print(f"CONTROLLO CADUTO: la fonte {nome} non contiene il fatto {ins}")
                return 1
            prop = f"Il commit «{sog}» ha aggiunto {ins} inserzioni."
            ric = mem.add(prop, topic=f"dl/{nome}/{ins}", source=fonte, validate="full")
            g = float(ric.get("grounding_score") or -1)
            st = str(ric.get("status"))
            if st != "quarantined":
                conta[nome] += 1
            celle.append(f"{'ENTRA' if st != 'quarantined' else 'ferma'} {g:6.1f}")
        print(f"  {ins:>6}   " + "".join(f"{c:>15}" for c in celle))

    print()
    for k, v in conta.items():
        print(f"  {k:<8} {v} su {QUANTI} ammessi")

    print()
    if conta["minima"] >= QUANTI - 1 and conta["intera"] <= 1:
        print("  => E' LA TAGLIA DELLA FONTE: gli stessi fatti VERI passano quando la")
        print("     fonte e' la sola riga che li sostiene, e vengono rifiutati quando la")
        print("     stessa riga sta dentro il documento intero. Falso negativo per")
        print("     diluizione, su fonte reale.")
    elif conta["minima"] <= 1:
        print("  => NON e' la taglia: i fatti veri sono rifiutati anche sulla fonte")
        print("     minima, dove il testo E' la loro prova. La causa e' altrove e non")
        print("     l'ho isolata.")
    else:
        print("  => quadro intermedio: guarda i numeri riga per riga.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
