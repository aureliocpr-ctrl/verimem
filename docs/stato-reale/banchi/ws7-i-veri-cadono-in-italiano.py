# -*- coding: utf-8 -*-
"""I CLAIM VERI CADONO PIU' IN ITALIANO CHE IN INGLESE? — la popolazione che manca

PERCHE' ESISTE. Il banco del vertice (`ws7-il-vertice-serve-a-qualcosa.py`) ha
trovato, su UN caso, che la stessa affermazione vera e' fermata in italiano e
ammessa in inglese:

    IT  «Il collaudo dell'impianto e' stato completato con esito positivo.»  -> quarantined 99.98
    EN  «The commissioning of the plant was completed successfully.»          -> AMMESSO     99.98

**n=1.** Da un caso non si ricava un tasso, e la cella lo dichiara. Questo banco
gli da' una popolazione: **dieci claim VERI per lingua**, ognuno sostenuto
LETTERALMENTE dalla propria fonte, e conta quanti ne cadono di qua e di la'.

E' costruito per POTER FALSIFICARE il sospetto: se i veri cadono in numero
uguale nelle due lingue, il caso del vertice era un caso e va detto.

LE DUE POPOLAZIONI, perche' un conteggio sui soli veri non e' leggibile:
    VERI   dieci per lingua, tutti letteralmente nella fonte -> devono passare
    FALSI  due per lingua, cifra inventata                   -> devono essere fermati
Se i FALSI non venissero fermati, il gate sarebbe spento e il conto sui veri
non significherebbe niente: e' il controllo che deve poter fallire.

LE TRADUZIONI sono fedeli e parallele di proposito: stesso ordine, stessi
numeri, stessa struttura sintattica. Se cambiassi anche il contenuto non
saprei attribuire una differenza alla lingua.

    python docs/stato-reale/banchi/ws7-i-veri-cadono-in-italiano.py

Store TEMPORANEO via `HIPPO_DATA_DIR`. Fuori da pytest (li' l'embedder e' uno
stub su SHA-256 e misurerebbe il righello).
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

FONTE_IT = (
    "Relazione tecnica del 4 aprile. Il collaudo dell'impianto e' stato completato con esito "
    "positivo. La potenza installata e' di 320 kW. Il costo sostenuto per l'intervento e' di "
    "48000 euro. Il responsabile del procedimento e' l'ingegner Rossi. I lavori sono iniziati "
    "il 12 gennaio e si sono conclusi il 28 marzo. La ditta esecutrice ha sede a Bologna. "
    "L'impianto serve tre edifici. La garanzia ha durata di ventiquattro mesi. Il collaudo non "
    "ha riguardato la linea secondaria, che resta esclusa dalla garanzia."
)
FONTE_EN = (
    "Technical report of 4 April. The commissioning of the plant was completed successfully. "
    "The installed power is 320 kW. The cost of the work was 48000 euro. The officer in charge "
    "is engineer Rossi. The works started on 12 January and ended on 28 March. The contractor "
    "is based in Bologna. The plant serves three buildings. The warranty lasts twenty-four "
    "months. The commissioning did not cover the secondary line, which remains excluded from "
    "the warranty."
)

VERI_IT = [
    "Il collaudo dell'impianto e' stato completato con esito positivo.",
    "La potenza installata e' di 320 kW.",
    "Il costo sostenuto per l'intervento e' di 48000 euro.",
    "Il responsabile del procedimento e' l'ingegner Rossi.",
    "I lavori sono iniziati il 12 gennaio.",
    "I lavori si sono conclusi il 28 marzo.",
    "La ditta esecutrice ha sede a Bologna.",
    "L'impianto serve tre edifici.",
    "La garanzia ha durata di ventiquattro mesi.",
    "La linea secondaria resta esclusa dalla garanzia.",
]
VERI_EN = [
    "The commissioning of the plant was completed successfully.",
    "The installed power is 320 kW.",
    "The cost of the work was 48000 euro.",
    "The officer in charge is engineer Rossi.",
    "The works started on 12 January.",
    "The works ended on 28 March.",
    "The contractor is based in Bologna.",
    "The plant serves three buildings.",
    "The warranty lasts twenty-four months.",
    "The secondary line remains excluded from the warranty.",
]
FALSI_IT = [
    "La potenza installata e' di 850 kW.",
    "Il costo sostenuto per l'intervento e' di 12000 euro.",
]
FALSI_EN = [
    "The installed power is 850 kW.",
    "The cost of the work was 12000 euro.",
]


def _giro(Memory, radice: Path, lingua: str, fonte: str, veri: list, falsi: list) -> tuple:
    mem = Memory(str(radice / f"veri_{lingua}.db"))
    caduti, passati_falsi = [], []
    print(f"\n  ===== {lingua} =====")
    for i, claim in enumerate(veri):
        ric = mem.add(claim, topic=f"veri/{lingua}/{i}", source=fonte, validate="full")
        stato, g = str(ric.get("status")), float(ric.get("grounding_score") or -1)
        if stato == "quarantined":
            caduti.append((claim, g))
            print(f"  🔴 VERO FERMATO  {g:6.2f}  {claim[:62]}")
    for i, claim in enumerate(falsi):
        ric = mem.add(claim, topic=f"falsi/{lingua}/{i}", source=fonte, validate="full")
        if str(ric.get("status")) != "quarantined":
            passati_falsi.append(claim)
    print(f"  veri fermati: {len(caduti)}/{len(veri)}   ·   "
          f"falsi passati (controllo): {len(passati_falsi)}/{len(falsi)}")
    return caduti, passati_falsi


def main() -> int:
    # Controllo che DEVE poter fallire: ogni claim VERO sta nella fonte, i falsi no.
    for tok in ("850", "12000"):
        if tok in FONTE_IT or tok in FONTE_EN:
            print(f"  CONTROLLO CADUTO: «{tok}» e' in una fonte")
            return 1
    if len(VERI_IT) != len(VERI_EN):
        print("  CONTROLLO CADUTO: le due liste non sono parallele")
        return 1
    print(f"  controllo retto: {len(VERI_IT)} veri per lingua, liste parallele, "
          "cifre inventate assenti dalle fonti")

    from verimem.client import Memory  # noqa: PLC0415

    radice = Path(tempfile.mkdtemp())
    it_c, it_f = _giro(Memory, radice, "IT", FONTE_IT, VERI_IT, FALSI_IT)
    en_c, en_f = _giro(Memory, radice, "EN", FONTE_EN, VERI_EN, FALSI_EN)

    print("\n  " + "=" * 78)
    print(f"  VERI FERMATI:   IT {len(it_c)}/{len(VERI_IT)}   ·   EN {len(en_c)}/{len(VERI_EN)}")
    print(f"  controllo:      falsi passati IT {len(it_f)}/2 · EN {len(en_f)}/2 "
          "(se non sono 0, il gate e' spento e il conto sopra non significa niente)")
    if len(it_c) == len(en_c):
        print("  ⇒ NESSUNA DIFFERENZA fra le due lingue: il caso del vertice era un caso.")
    else:
        print(f"  ⇒ DIFFERENZA: {abs(len(it_c) - len(en_c))} claim veri di scarto "
              f"a favore di {'EN' if len(it_c) > len(en_c) else 'IT'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
