"""LIVELLO: porta del prodotto (`Memory.add`, `validate="full"`).

Quali claim la frase estranea ribalta, e quali no — quattro celle incrociate.

    python docs/stato-reale/banchi/ws3-quali-claim-la-zavorra-ribalta-quattro-celle.py

⚠️ Carica il giudice (~30 s di freddo). Otto scritture, ~35 s in tutto.

━━ PERCHE' ESISTE, ED E' UNA CORREZIONE A UN BANCO MIO ━━━━━━━━━━━━━━━━━━━━━━
`ws3-una-frase-estranea-vale-98-punti-di-grounding.py` misura +98,10 su due
claim. `ws3-trenta-coppie-con-e-senza-frase-estranea.py` misura **0 su 30** e
una mediana di **+0,7** su trenta contraddizioni generate con una regola fissa.
I due numeri sono entrambi veri e sembrano incompatibili: questo banco tiene i
casi che li conciliano, cosi' chi vuole misurare la zavorra sa QUALI frasi
usare — e chi usa le trenta sapendo solo il titolo non spreca un giro.

━━ MISURATO IL 2026-09-03 alle 20:24, stesso verbale, stessa zavorra ━━━━━━━━
    claim                            corta            + zavorra          esito
    confermato, «e'» con apostrofo   quar.  g= 1,84   model_claim 99,94  RIBALTA
    confermato, «e» nuda             quar.  g= 3,92   quar.       99,95  no
    in carica,  «e'» con apostrofo   quar.  g= 0,73   quar.       32,11  no
    in carica,  «e» nuda             quar.  g= 0,93   model_claim 99,90  RIBALTA

TRE COSE CHE QUESTA TABELLA DICE, e nessuna e' quella che avevo detto io:
① **Il salto del giudice non e' il ribaltamento.** Tre righe su quattro
   arrivano sopra 99, ma solo due entrano: la seconda ha grounding **99,95** e
   resta TRATTENUTA. ⇒ punteggio del giudice e tasso di ammissione sono due
   misure diverse e non vanno usate una per l'altra.
② **La grafia conta.** Sullo stesso claim («in carica»), scrivere «e» invece di
   «e'» porta l'effetto della zavorra da **+31,4** a **+98,97**.
③ **Quindi le trenta coppie non potevano vedere il fenomeno**: sono generate
   con «e'», la forma corretta. Lo 0/30 e' un numero vero su una popolazione
   che, per come l'ho costruita, era fuori portata.

⚠️ QUELLO CHE NON DICE, e non lo riempio: PERCHE' la grafia conti, e se sia il
solo fattore. Quattro celle non sono un modello. Chi volesse chiuderlo deve
generare due popolazioni identiche salvo la grafia — non l'ho fatto.
📎 Terreno vicino: `c857752e` (30/08) aggiunse `e'` ai marcatori di verbo di
`subject_extract`. Non affermo che sia la stessa causa: dico che e' lo stesso
terreno, e che chi indaga qui parta da li'.

━━ A CHI SERVE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Per confrontare MODELLI diversi sulla zavorra servono le due righe che
RIBALTANO, non le trenta coppie. Le trenta restano utili per un'altra domanda —
«il modello vede la contraddizione?», dove danno 24/30 trattenuti.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from verimem.client import Memory

FONTE = "Verbale: il direttore ha rassegnato le dimissioni il 4 maggio."
ZAVORRA = "La mensa aziendale resta chiusa il primo maggio."

#: due claim x due grafie. L'unica differenza fra le righe 1-2 e fra le 3-4 e'
#: l'apostrofo: e' la variabile isolata.
CLAIM = [
    ("confermato, e' con apostrofo",
     "Il direttore e' stato confermato nell'incarico il 4 maggio.", True),
    ("confermato, e nuda",
     "Il direttore e stato confermato nell'incarico il 4 maggio.", False),
    ("in carica,  e' con apostrofo",
     "Il direttore e' ancora in carica il 4 maggio.", False),
    ("in carica,  e nuda",
     "Il direttore e ancora in carica il 4 maggio.", True),
]


def main() -> None:
    mem = Memory(str(Path(tempfile.mkdtemp()) / "quali.db"))
    print("QUALI CLAIM LA ZAVORRA RIBALTA\n")
    print(f"{'claim':32s} {'corta':>20s} {'+ zavorra':>20s}   esito  atteso")
    for i, (nome, claim, atteso) in enumerate(CLAIM):
        a = mem.add(claim, topic=f"t/quali/{i}/corta", source=FONTE, validate="full")
        b = mem.add(claim, topic=f"t/quali/{i}/zav",
                    source=f"{FONTE} {ZAVORRA}", validate="full")
        ga, gb = a.get("grounding_score"), b.get("grounding_score")
        sa, sb = str(a.get("status")), str(b.get("status"))
        rib = sa == "quarantined" and sb != "quarantined"
        segno = "✅" if rib == atteso else "🔴 DIVERSO DA COME FU MISURATO"
        print(f"{nome:32s} {sa[:10]:>10s} g={ga if ga is None else round(ga, 2):>7} "
              f"{sb[:10]:>10s} g={gb if gb is None else round(gb, 2):>7}   "
              f"{'RIBALTA' if rib else 'no':>7}  {segno}", flush=True)
    print()
    print("  Se una riga stampa 🔴 il comportamento e' cambiato dal 03/09:")
    print("  e' una buona notizia o una regressione, ma va guardata.")


if __name__ == "__main__":
    main()
