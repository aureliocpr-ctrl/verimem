# -*- coding: utf-8 -*-
r"""BASTA UN'INTESTAZIONE: 17 parole che non dicono niente portano il falso da 7.9 a 99.1.

    PERTINENTI   (25 parole)  VERO=persist 99.9   FALSO=persist   99.8
    NEUTRE       (19 parole)  VERO=persist 99.8   FALSO=persist   99.9
    RIEMPIMENTO  (17 parole)  VERO=persist 99.4   FALSO=persist   99.1   <- vuote
    sola         ( 7 parole)  VERO=persist 99.6   FALSO=downgrade  7.9

Claim identico ovunque: «La consegna e' prevista per LUNEDI'» contro una fonte che
dice GIOVEDI'. Il VERO passa in tutte e quattro le celle: il banco separa.

PAGA IL DEBITO di `ws5-bastano-venticinque-parole.py`: «le frasi aggiunte erano VERE e
PERTINENTI, non ho separato *piu' testo* da *piu' fatti concorrenti*».

⇒ ① E' LA LUNGHEZZA, NON LA CONCORRENZA. Le tre celle piene si comportano uguale
(99.1-99.9) e differiscono solo dalla cella «sola». **Non conta cosa dicono le altre
frasi: conta che ci siano.**
⇒ ② E IL CASO PEGGIORE E' IL RIEMPIMENTO PURO: «Nota interna. Documento di servizio.
Copia per archivio. Pagina uno.» — quattro frasi che **non affermano nulla** — bastano.
**Diciassette parole.**
⇒ ③ QUELLA E' L'INTESTAZIONE DI QUALUNQUE DOCUMENTO AZIENDALE. Non serve un attaccante,
non serve un contratto, non servono fatti concorrenti: **serve un'intestazione**. Un
documento senza intestazione non esiste ⇒ **in pratica il caso «sola» non si presenta
mai fuori da un banco.**

⚠️ E RIBALTA LA MIA LETTURA DI IERI su `ws5-l-affermazione-vince-sulla-collisione.py`,
dove allungare la fonte ABBASSAVA il punteggio del falso (0.5 → 0.2). ⇒ Li' il valore
era **numerico** e `L4.1` restava in campo; qui e' un giorno della settimana, `L4.1` non
partecipa, e l'effetto della lunghezza si **inverte**. **Lo stesso allungamento protegge
i numeri ed espone tutto il resto.**

⚖️ PUNTO DEBOLE: un solo claim, un solo tipo di valore, quattro celle. E le tre celle
piene hanno lunghezze diverse (17/19/25) — **non ho isolato la lunghezza esatta**: so
che 7 difende e 17 no, non dove stia il confine. Serve una scala fine fra 7 e 17.

REGIME: build corrente · python 3.13.12 · store temporaneo · `run_validation_gate`
(la porta della CLI, `cli.py:1867`) · letti i `warnings`, non `layers`.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-basta-un-intestazione.py <dir-temp>
⚠️ Vuole una dir TEMPORANEA.
"""
import os, sys
os.environ["HIPPO_DATA_DIR"] = sys.argv[1]
from verimem.anti_confab_gate import run_validation_gate

ANC = "La consegna e' prevista per giovedi'. "
PERT = ("Il responsabile del cantiere e' Rossi; il custode delle chiavi e' Mancini. "
        "Il cantiere non e' stato sospeso. ")
NEUT = ("La mensa aziendale apre alle dodici. Il parcheggio visitatori e' sul retro. ")
RIEMP = ("Nota interna. Documento di servizio. Copia per archivio. Pagina uno. ")

FONTI = [("PERTINENTI", "Verbale: " + PERT + ANC),
         ("NEUTRE",     "Verbale: " + NEUT + ANC),
         ("RIEMPIMENTO","Verbale: " + RIEMP + ANC),
         ("sola",       "Verbale: " + ANC)]
CLAIM = [("VERO", "La consegna e' prevista per giovedi'."),
         ("FALSO", "La consegna e' prevista per lunedi'.")]
print("")
for eti_f, src in FONTI:
    out = []
    for eti_c, claim in CLAIM:
        r = run_validation_gate(proposition=claim, verified_by=None, topic=None,
                                agent=None, source=src, grounding_llm=None, ground_write=True)
        g = getattr(r, "grounding_score", None)
        out.append("%s=%-9s g=%5s" % (eti_c[:5], getattr(r, "action", "?")[:9],
                   ("%.1f" % g) if isinstance(g, (int, float)) else "-"))
    print("   %-13s (%2d parole)  %s" % (eti_f, len(src.split()), "  ".join(out)))
