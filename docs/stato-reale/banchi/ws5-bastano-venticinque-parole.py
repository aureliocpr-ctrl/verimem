# -*- coding: utf-8 -*-
r"""BASTANO 25 PAROLE: la stessa affermazione, diluita, smette di essere difesa.

    1 frase  ( 7 parole)   VERO=persist  99.8   FALSO=downgrade 11.4
    2 frasi  (13 parole)   VERO=persist 100.0   FALSO=downgrade  8.2
    4 frasi  (25 parole)   VERO=persist  99.9   FALSO=persist   99.8   <- passa

Claim identico in tutte e tre le celle: «La consegna e' prevista per LUNEDI'» contro
una fonte che dice **GIOVEDI'**. Cambia solo quante altre frasi accompagnano
l'affermazione. Il controllo positivo (il VERO) passa in tutte e tre: il banco separa.

⇒ ① LA SOGLIA E' FRA 13 E 25 PAROLE. Non 200 (`ws5-Q2bis-la-rarita-del-numero-decide`),
non 4500 (`ws5-Q2-il-gate-annega-sulle-fonti-lunghe`): **venticinque**. Quelle misure
erano su valori NUMERICI, dove `L4.1` fa da rete finche' regge; qui il valore e' un
giorno della settimana — **nessuna cifra, nessun layer lessicale**, e resta solo il
giudice semantico, che si diluisce subito.
⇒ ② E QUALIFICA LA REGOLA CHE AVEVO SCRITTO IERI. «Il gate difende cio' che il testo
AFFERMA» e' vero **solo se l'affermazione e' ISOLATA o quasi**. In un verbale di
quattro frasi, l'affermazione non centrale **non e' piu' difesa** — e un verbale di
quattro frasi e' il documento piu' corto che esista in un ufficio.
⇒ ③ SI SALDA COL CONTORNO NEUTRO (`ws5-ricombinare-i-token-della-fonte-da-100`: cinque
frasi estranee portano 1.1 -> 100.0). **Stesso meccanismo, misurato dall'altro lato:**
li' aggiungevo rumore attorno a un claim gia' falso; qui aggiungo CONTENUTO VERO attorno
a un'affermazione vera, e il falso che la contraddice smette di essere visto.
⚠️ ⇒ **Non serve un attaccante e non serve un contratto: basta un verbale normale.**

⚖️ PUNTO DEBOLE: un solo claim, un solo tipo di valore (giorno della settimana), tre
celle. **Misura il meccanismo, non la soglia generale**: su un valore piu' saliente —
un importo, un nome proprio — la diluizione potrebbe richiedere piu' testo. E le frasi
aggiunte qui sono VERE e pertinenti: non ho separato «piu' testo» da «piu' fatti
concorrenti».

REGIME: build corrente · python 3.13.12 · store temporaneo · `run_validation_gate`
(la porta della CLI, `cli.py:1867`) · letti i `warnings`, non `layers` (che nella
ricevuta non esiste — reperto di @ws3).

RIPRODUCI:  python docs/stato-reale/banchi/ws5-bastano-venticinque-parole.py <dir-temp>
⚠️ Vuole una dir TEMPORANEA.
"""
import os, sys
os.environ["HIPPO_DATA_DIR"] = sys.argv[1]
from verimem.anti_confab_gate import run_validation_gate

ANC = "La consegna e' prevista per giovedi'. "
ALTRE = ("Il responsabile del cantiere e' Rossi; il custode delle chiavi e' Mancini. "
         "Il cantiere non e' stato sospeso. ")
FONTI = [("1 frase (sola)", "Nota: " + ANC),
         ("2 frasi",        "Nota: " + ANC + "Il responsabile del cantiere e' Rossi. "),
         ("4 frasi",        "Verbale: " + ALTRE + ANC)]
CLAIM = [("VERO giovedi", "La consegna e' prevista per giovedi'."),
         ("FALSO lunedi", "La consegna e' prevista per lunedi'.")]
print("")
for eti_f, src in FONTI:
    out = []
    for eti_c, claim in CLAIM:
        r = run_validation_gate(proposition=claim, verified_by=None, topic=None,
                                agent=None, source=src, grounding_llm=None, ground_write=True)
        g = getattr(r, "grounding_score", None)
        out.append("%s=%-9s g=%5s" % (eti_c.split()[0][:5], getattr(r, "action", "?")[:9],
                   ("%.1f" % g) if isinstance(g, (int, float)) else "-"))
    print("   %-16s (%3d parole)  %s" % (eti_f, len(src.split()), "  ".join(out)))
