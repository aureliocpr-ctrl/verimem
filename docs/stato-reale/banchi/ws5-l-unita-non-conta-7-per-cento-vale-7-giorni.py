# -*- coding: utf-8 -*-
r"""«Una penale del 7%» nella fonte VALIDA «un preavviso di 7 giorni» nel claim.

    7% nella fonte, claim «7 giorni»                assenti=0   <- NON rilevato
    7 giorni nella fonte, claim «7%»                assenti=0   <- NON rilevato
    7% nella fonte, claim «7%» (vero)               assenti=0   <- corretto
    CONTROLLO: 99 assente ovunque                   assenti=1   [99.0 giorno]  ✓
    3.5 gradi nella fonte, claim «3.5%»             assenti=0   <- NON rilevato
    3.5 gradi nella fonte, claim «35 gradi»         assenti=1   [35.0 grado]   ✓

⇒ L'UNITA' NON ENTRA NEL CONFRONTO: `valori_non_nella_fonte` confronta il VALORE
NUDO. Una fonte che parla di una penale percentuale valida un claim che parla di
giorni di preavviso, purche' il numero coincida.
⚠️ E NON SERVE UNA FONTE LUNGA: qui bastano DUE FRASI. Il banco Q2 diceva «serve
un documento», il Q2bis «bastano 200 parole se il numero e' comune» — questo dice
**basta una frase con lo stesso numero in un'altra unita'**.

🔑 LA CAPACITA' C'E' E NON E' COLLEGATA — terza volta oggi. `ValoreAssente` PORTA il
campo `.unita`, e si vede nell'output stesso: il controllo stampa `[99.0 giorno]` e
`[35.0 grado]`. L'unita' viene **estratta e portata fino in fondo**, e poi **non usata
per decidere**. Non e' un dato mancante: e' un dato presente e ignorato.
⇒ Stessa forma di `valori_scritti_a_parole` (esiste, generica, chiamata su un lato
solo) e di `telemetry_analyzer` («completo e irraggiungibile da ogni superficie»).

🚨 PERCHE' E' IL CASO PEGGIORE DELLA SERIE. Un contratto e' pieno di percentuali E di
giorni E di rate, e i numeri piccoli si ripetono per forza: «penale 7%», «preavviso 7
giorni», «7 rate». ⇒ Su un documento vero **ogni valore piccolo del claim trova un
gemello in un'altra unita'**, e `L4.1` — che e' l'unico strato che regge — tace.
⇒ Le tre condizioni misurate oggi si sommano: il numero deve essere **in cifra** (se
e' a parole non lo vede), **raro** (se e' comune collide a 200 parole), e **con
un'unita' che non compare altrove** (che non e' nemmeno una condizione: l'unita' non
la guarda).

✅ IL CONTROLLO CHE DOVEVA FALLIRE HA TENUTO: il valore 99, assente dalla fonte in
qualsiasi unita', risulta assente. E il caso `35` contro `3.5` e' corretto — i
decimali non si confondono con gli interi. **Il difetto e' specifico dell'unita', non
un guasto generale del confronto.**

⚖️ PUNTO DEBOLE, dichiarato io: **le fonti sono COSTRUITE**, non estratte da un
documento vero, perche' servivano coppie unita'-diversa/valore-uguale che in un testo
reale non si trovano su richiesta. Sei casi, due controlli dentro. ⇒ La misura dice
che il meccanismo esiste; **non dice quanto sia frequente su contratti veri** — per
quello serve un corpus legale, che non ho.

REGIME: build `f5dedf34` · python 3.13.12 · store temporaneo · chiamata diretta a
`valori_non_nella_fonte`, la funzione su cui `L4.1` decide (`anti_confab_gate.py:2455`).

RIPRODUCI:  python docs/stato-reale/banchi/ws5-l-unita-non-conta-7-per-cento-vale-7-giorni.py <dir-temp>
⚠️ Vuole una dir TEMPORANEA.
"""
import os, sys
os.environ["HIPPO_DATA_DIR"] = sys.argv[1]
from verimem.valore_non_nella_fonte import valori_non_nella_fonte

#: (etichetta, fonte, claim)  — il claim inventa SEMPRE un valore che la fonte
#: non afferma con QUELLA unita'.
CASI = [
 ("7% nella fonte, claim «7 giorni»",
  "Il contratto prevede una penale del 7% sul valore residuo.",
  "Il contratto prevede un preavviso di 7 giorni."),
 ("7 giorni nella fonte, claim «7%»",
  "Il contratto prevede un preavviso di 7 giorni.",
  "Il contratto prevede una penale del 7%."),
 ("7% nella fonte, claim «7%» (stessa unita', VERO)",
  "Il contratto prevede una penale del 7% sul valore residuo.",
  "Il contratto prevede una penale del 7%."),
 ("CONTROLLO: 99 assente ovunque",
  "Il contratto prevede una penale del 7% sul valore residuo.",
  "Il contratto prevede un preavviso di 99 giorni."),
 ("decimale: 3.5 nella fonte, claim «3.5%» altra grandezza",
  "La temperatura registrata e' 3.5 gradi.",
  "L'aumento registrato e' del 3.5%."),
 ("decimale: 3.5 nella fonte, claim «35»",
  "La temperatura registrata e' 3.5 gradi.",
  "La temperatura registrata e' 35 gradi."),
]
print("")
for eti, src, claim in CASI:
    ass = valori_non_nella_fonte(claim, src)
    det = ", ".join("%s%s" % (getattr(v, "valore", v), (" " + v.unita) if getattr(v, "unita", "") else "")
                    for v in ass) or "-"
    print("   %-46s assenti=%d  [%s]" % (eti[:46], len(ass), det[:40]))
