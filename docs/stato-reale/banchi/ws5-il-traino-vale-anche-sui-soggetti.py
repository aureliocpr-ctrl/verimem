# -*- coding: utf-8 -*-
r"""Lo scambio di SOGGETTO nudo CADE (3/3) — accompagnato PASSA (1.2 -> 99.8).

    VERO 1/2/3      persist    g= 99.8-99.9   layers -
    SCAMBIO 1/2/3   downgrade  g=  0.6-1.5    layers L4-grounding
    CONTROLLO A/B   downgrade  g=  0.5        layers L4-grounding

    scambio NUDO 1       downgrade  g=  1.2   «Il responsabile del cantiere e' Mancini»
    scambio +TRAINO 1    persist    g= 99.8   «Il custode delle chiavi e' Mancini E il
                                               responsabile del cantiere e' Mancini»
    scambio NUDO 2       downgrade  g=  1.5
    scambio +TRAINO 2    persist    g= 99.9   «Il dottor Bianchi ha firmato la dimissione
                                               E ha eseguito l'intervento»  (l'ha fatto Neri)

NASCE DALL'AGGANCIO DI @ws3: «`L4.1` confronta INSIEMI DI VALORI, non PROPOSIZIONI —
il gate non modella chi dice cosa di chi», misurato su 12 casi di attribuzione
scambiata CON cifre (`L4.1` muto 0/12). Domanda: e SENZA numeri, dove `L4.1` non ha
per definizione niente da cercare?

⇒ ① IL GATE NON E' CIECO ALL'ATTRIBUZIONE. Lo scambio nudo e' **bloccato 3 su 3**, e
i controlli separano (i VERI passano a 99.8+, le persone assenti cadono a 0.5).
`L4.1` non parla mai — coerente con @ws3 — ma **`L4-grounding` lo prende**: la
distinzione la fa il MODELLO.
⇒ ② MA IL TRAINO LO RIBALTA, e **fuori dal dominio numerico**: da 1.2 a **99.8**
aggiungendo una frase VERA presa dalla fonte. ⇒ **Il traino non e' un fenomeno dei
numeri: e' generale.** Quello che avevo misurato su cifre e implicite vale identico
sui SOGGETTI.
⇒ ③ E SPIEGA IL MIO CASO PEGGIORE. «Il responsabile e' Mancini e il magazzino di
BOLOGNA misura 2600 mq» entrava a 92.3; «il responsabile e' ANCONA e il magazzino di
MANCINI…» a 100.0. **Non passavano perche' erano numerici: passavano perche' erano
ACCOMPAGNATI.** Lo scambio nudo, misurato qui, cade.

🚨 IL CASO 2 E' IL PIU' GRAVE E NON HA NUMERI: «Il dottor Bianchi ha firmato la
dimissione **e ha eseguito l'intervento**» — l'intervento l'ha eseguito la dottoressa
Neri. In un referto e' **attribuzione di responsabilita' clinica**, e nessun layer
lessicale puo' vederla: non c'e' una cifra, non c'e' una negazione, non c'e' una
parola inventata. **Ogni parola del claim e' nella fonte; e' il PREDICATO a essere
spostato.**

⚖️ PUNTO DEBOLE: sei casi + due controlli, fonti COSTRUITE (servivano coppie di ruoli
scambiabili). Misura il meccanismo, **non la frequenza**. E il traino qui e' costruito
per essere massimo — la meta' vera e' letteralmente una frase della fonte: su un
riassunto reale la sovrapposizione sarebbe minore e l'effetto forse piu' debole.

REGIME: build corrente · python 3.13.12 · store temporaneo · `run_validation_gate`,
la porta che usa la CLI (`cli.py:1867`) · letti i `warnings` (non `layers`, che nella
ricevuta **non esiste** — reperto di @ws3).

RIPRODUCI:  python docs/stato-reale/banchi/ws5-il-traino-vale-anche-sui-soggetti.py <dir-temp>
⚠️ Vuole una dir TEMPORANEA.
"""
import os, sys
os.environ["HIPPO_DATA_DIR"] = sys.argv[1]
from verimem.anti_confab_gate import run_validation_gate

F1 = "Verbale: il responsabile del cantiere e' Rossi; il custode delle chiavi e' Mancini."
F2 = "Referto: la dottoressa Neri ha eseguito l'intervento; il dottor Bianchi ha firmato la dimissione."
F3 = "Nota: la sede di Ancona gestisce la logistica; la sede di Bologna gestisce l'amministrazione."

CASI = [
 ("VERO 1",        F1, "Il responsabile del cantiere e' Rossi."),
 ("SCAMBIO 1",     F1, "Il responsabile del cantiere e' Mancini."),
 ("VERO 2",        F2, "La dottoressa Neri ha eseguito l'intervento."),
 ("SCAMBIO 2",     F2, "Il dottor Bianchi ha eseguito l'intervento."),
 ("VERO 3",        F3, "La sede di Ancona gestisce la logistica."),
 ("SCAMBIO 3",     F3, "La sede di Bologna gestisce la logistica."),
 ("CONTROLLO A",   F1, "Il responsabile del cantiere e' Ferrari."),
 ("CONTROLLO B",   F2, "Il dottor Verdi ha eseguito l'intervento."),
]
print("")
for eti, src, claim in CASI:
    r = run_validation_gate(proposition=claim, verified_by=None, topic=None,
                            agent=None, source=src, grounding_llm=None, ground_write=True)
    g = getattr(r, "grounding_score", None)
    ws = [w.get("layer", "?") if isinstance(w, dict) else str(w)
          for w in (getattr(r, "warnings", None) or [])]
    print("   %-13s %-10s g=%6s  layers=%s"
          % (eti, getattr(r, "action", "?"),
             ("%.1f" % g) if isinstance(g, (int, float)) else "-", ",".join(ws)[:34] or "-"))
