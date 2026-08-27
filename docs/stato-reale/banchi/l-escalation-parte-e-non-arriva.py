# -*- coding: utf-8 -*-
"""LA PROVA CHE I QUARANTA SECONDI SONO L'ESCALATION — spegnendola.

Il 2x2 ha separato le due variabili: a parita' di fonte (2000 caratteri) il
claim col punteggio centrale costa 43630 ms e quello col punteggio estremo 208.
E' la BANDA a costare, non la lunghezza.

`band_escalation.py:1` dichiara: «CE-band -> llm-judge escalation: the moat's
uncertain middle gets a real verdict», e `anti_confab_gate.py:2666` la invoca
quando `gscore < _ce_band_tau_hi()`. Il modulo dichiara anche l'interruttore:
«ENGRAM_BAND_LLM=0 opts out».

⇒ Se i quaranta secondi sono l'escalation, spegnendola la stessa cella diventa
veloce E il punteggio non cambia (perche' l'escalation, nelle mie misure, non
ha mai sostituito il verdetto: la ricevuta riporta sempre local_gate_ce_v2).
Se invece resta lenta, l'escalation non c'entra e la mia lettura cade di nuovo.

E' un A/B nella STESSA esecuzione: immune alla copia di lavoro che si muove.

    python docs/stato-reale/banchi/l-escalation-parte-e-non-arriva.py
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path

DOC = Path("docs/archive/2026-05-13_FORGIA.md")
FALSO = "Il file wake.py conta 9999 LOC."


def main() -> int:
    if not DOC.exists():
        print(f"NON RIUSCITO: {DOC} non c'e'")
        return 1
    fonte = DOC.read_text(encoding="utf-8", errors="replace")[:2000]

    from verimem.client import Memory  # noqa: PLC0415

    mem = Memory(str(Path(tempfile.mkdtemp()) / "ab.db"))

    def giro(etichetta: str) -> tuple[float, float, str]:
        t0 = time.monotonic()
        ric = mem.add(FALSO, topic=f"ab/{etichetta}", source=fonte, validate="full")
        ms = (time.monotonic() - t0) * 1000
        g = float(ric.get("grounding_score") or -1)
        j = json.dumps(ric.get("adjudication"), default=str)
        judge = "?"
        for tok in ('"model": "', '"backend": "'):
            if tok in j:
                judge = j.split(tok, 1)[1].split('"', 1)[0]
                break
        print(f"  {etichetta:<28} {g:6.1f}  {ms:8.0f} ms   judge={judge}")
        return g, ms, judge

    print("  cella                        ground        ms")
    print("  " + "-" * 62)
    os.environ.pop("ENGRAM_BAND_LLM", None)
    g_on, ms_on, _ = giro("A escalation ACCESA")
    os.environ["ENGRAM_BAND_LLM"] = "0"
    g_off, ms_off, _ = giro("B escalation SPENTA")
    os.environ.pop("ENGRAM_BAND_LLM", None)
    g_on2, ms_on2, _ = giro("C riaccesa, controllo")

    print("\n  Il controllo C serve a escludere che B sia veloce solo perche' e'")
    print("  il secondo giro: se C torna lenta, la differenza e' l'interruttore.")
    if ms_off * 5 < ms_on and ms_off * 5 < ms_on2:
        print(f"\n  ⇒ CONFERMATO: {ms_on:.0f} / {ms_off:.0f} / {ms_on2:.0f} ms.")
        print("    I quaranta secondi sono l'escalation della banda.")
        if abs(g_on - g_off) < 0.5:
            print(f"    E il punteggio non cambia ({g_on:.1f} contro {g_off:.1f}):")
            print("    l'escalation parte, costa, e NON sostituisce il verdetto.")
            print("    ⇒ il rimedio dichiarato dal prodotto non arriva, e la")
            print("      ricevuta non dice che ci ha provato.")
        else:
            print(f"    E il punteggio CAMBIA: {g_on:.1f} con, {g_off:.1f} senza.")
            print("    ⇒ l'escalation arriva e decide: e' un rimedio VIVO, e va detto.")
    elif ms_off * 5 >= ms_on:
        print(f"\n  ⇒ NON confermato: {ms_on:.0f} / {ms_off:.0f} / {ms_on2:.0f} ms.")
        print("    Spegnere l'escalation non cambia il tempo: non e' lei.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
