"""Il giudice di sufficienza chiude davvero il buco dell'astensione? — NON eseguito.

`trust_report` promette «or an EXPLICIT abstention when the memory holds nothing
relevant», e sul buco vero non la mantiene: alla domanda su un dato che il corpus
NON ha, risponde con il fatto più vicino. Misurato: con `ce_gate` acceso si
astiene 15/15 sulle domande di dominio estraneo e 0/15 su quelle in tema con il
dato assente — cioè cura il caso facile e lascia intatto quello vero.

Il secondo livello di astensione esiste ed è spento: il giudice di SUFFICIENZA,
quello che il docstring descrive come «a fact on-topic that names the RIGHT
SUBJECT IN THE WRONG ROLE». Vuole un provider LLM. Questo banco misura se
accenderlo chiude il buco, e NON SI ESEGUE senza un flag esplicito: accendere un
modello locale è RAM sulla macchina di chi decide, non una scelta del banco.

═══ IL CRITERIO, FISSATO IL 2026-08-26 ALLE 22:04, PRIMA DI AVERE IL MODELLO ═══

    oggi, giudice spento:  VICINE 0/15 astensioni · NOTE 0/15 astensioni

    SUCCESSO    VICINE >= 12/15   E   NOTE <= 1/15   (niente false astensioni)
    PARZIALE    VICINE fra 5 e 11 su 15
    FALLIMENTO  VICINE <= 4/15  ->  l'llm NON e' la cura, il difetto e' altrove

Scritto prima perché una soglia decisa dopo aver visto il numero non è una
soglia: è una descrizione. Se il risultato non rispetta questa griglia va detto
com'è, e questo file è qui perché nessuno — chi lo ha scritto per primo — possa
ritarare l'aspettativa a cose fatte.

═══ LE TRE POPOLAZIONI ═══

    NOTE    domande su fatti che il corpus HA          -> deve RISPONDERE
    VICINE  le stesse, con un identificatore cambiato
            o un attributo mai scritto                 -> deve ASTENERSI
    (le domande di dominio estraneo non servono: il pavimento CE le prende già
     15/15, e includerle gonfierebbe il risultato con il caso facile)

Il controllo che rende il numero leggibile è NOTE: un giudice che si astiene su
tutto otterrebbe 15/15 sulle VICINE ed è inutile. Il successo richiede ENTRAMBE
le colonne.

Run:  ENGRAM_LLM_BENCH=1 python -m benchmark.il_giudice_llm_fa_astenere
      (senza la variabile stampa cosa farebbe ed esce 0: e' un banco armato,
       non una misura che parte da sola)
Exit: 0 se ha misurato o se non era armato · 2 se armato ma senza provider,
      perche' allora i numeri direbbero solo che manca il modello.
"""
from __future__ import annotations

import os
import pathlib
import random
import re
import sqlite3
import sys

SEME = 20260826
SOGLIA_SUCCESSO_VICINE = 12
SOGLIA_MAX_FALSE = 1
QUANTE = 15


def _domande(db_path: str) -> tuple[list[str], list[str]]:
    c = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        rows = [r[0] for r in c.execute(
            "SELECT proposition FROM facts WHERE status != 'quarantined' "
            "AND superseded_by IS NULL AND length(proposition) BETWEEN 40 AND 160 "
            "ORDER BY created_at DESC LIMIT 400")]
    finally:
        c.close()
    campione = random.Random(SEME).sample(rows, min(QUANTE, len(rows)))
    note = [" ".join(p.split()[:9]) for p in campione]
    vicine = [
        re.sub(r"\b\d+\b", lambda m: str(int(m.group(0)) + 7717), d, count=1)
        if re.search(r"\d", d) else d + " e il suo colore di targa"
        for d in note
    ]
    return note, vicine


def main() -> int:
    if os.environ.get("ENGRAM_LLM_BENCH", "").strip() not in ("1", "on", "true", "yes"):
        print("  banco ARMATO e non eseguito.")
        print("  serve un provider llm attivo (es. `ollama serve`) e poi:")
        print("      ENGRAM_LLM_BENCH=1 python -m benchmark.il_giudice_llm_fa_astenere")
        print(f"  criterio gia' fissato: SUCCESSO se VICINE >= {SOGLIA_SUCCESSO_VICINE}/{QUANTE}"
              f" e NOTE <= {SOGLIA_MAX_FALSE}/{QUANTE}")
        return 0

    from verimem.config import CONFIG
    from verimem.llm import get_llm
    from verimem.semantic import SemanticMemory
    from verimem.trust_report import build_trust_report

    llm = get_llm()
    tipo = type(llm).__name__
    print(f"  provider risolto: {tipo}")
    if tipo == "MockLLM":
        print("  ⇒ nessun provider configurato: il giudice non girerebbe e i numeri")
        print("     direbbero solo questo. Non misuro.")
        return 2

    db = str(CONFIG.semantic_db)
    print(f"  corpus (SOLA LETTURA): {db}")
    note, vicine = _domande(db)
    sm = SemanticMemory(db_path=pathlib.Path(db))

    def astensioni(domande: list[str]) -> int:
        return sum(1 for q in domande
                   if build_trust_report(sm, q, k=3, ce_gate=True, llm=llm)["abstained"])

    a_vicine, a_note = astensioni(vicine), astensioni(note)
    print()
    print(f"  VICINE (dato ASSENTE, devono astenersi) : {a_vicine}/{len(vicine)}")
    print(f"  NOTE   (il corpus SA, non devono)       : {a_note}/{len(note)}  <- false astensioni")
    print()
    if a_vicine >= SOGLIA_SUCCESSO_VICINE and a_note <= SOGLIA_MAX_FALSE:
        print("  ⇒ SUCCESSO secondo il criterio del 26/08 22:04: l'llm chiude il buco.")
    elif a_vicine >= 5:
        print("  ⇒ PARZIALE secondo il criterio del 26/08 22:04.")
    else:
        print("  ⇒ FALLIMENTO secondo il criterio del 26/08 22:04: l'llm NON e' la cura,")
        print("     e il difetto va cercato altrove.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
