# -*- coding: utf-8 -*-
"""E' LA PAROLA «COLLAUDO» O LA POSIZIONE NELLA FONTE? — la variabile isolata

PERCHE' ESISTE. Il banco `ws7-la-data-fa-cadere-il-vero.py` ha falsificato
l'ipotesi «e' il tipo di dato» e ne ha lasciata una molto piu' stretta: su
diciotto claim VERI, gli unici tre fermati erano **le tre varianti della stessa
riga** — quella sul *collaudo* — mentre le altre cinque righe passavano quindici
volte su quindici. E lo stesso soggetto era caduto in un banco precedente, con
una fonte diversa.

DUE SPIEGAZIONI POSSIBILI, e questo banco le separa:

    H1  LESSICALE   e' la parola «collaudo» a fare qualcosa
    H2  POSIZIONALE e' la QUARTA riga di sei a essere trattata diversamente

Si separano tenendo fissa la struttura e cambiando UNA cosa per volta:
  - stessa posizione (quarta riga), OTTO parole diverse al suo posto
  - stessa parola («collaudo»), SEI posizioni diverse nella fonte

FORMA GEMELLA, e non e' mia: @ws6 il 28/08 alle 22:21 ha misurato che la parola
«nota» in una fonte **rende il gate cieco a tutti i numeri** (`nota/note/Nota/
NOTA` accecano, `notato/commento/alfa` no). Quello fa PASSARE il falso, questo
fa CADERE il vero: **direzioni opposte, stessa forma** — una parola specifica
nella fonte cambia il comportamento del gate. Se H1 regge, sono due istanze
della stessa classe.

CONTROLLO CHE DEVE POTER FALLIRE: per ogni parola, il claim e' costruito dalla
SUA fonte, quindi e' sempre VERO e letteralmente sostenuto. Se cadessero tutte,
non sarebbe la parola: sarebbe il banco.

    python docs/stato-reale/banchi/ws7-e-la-parola-o-la-posizione.py

Store TEMPORANEO via `HIPPO_DATA_DIR`. Fuori da pytest.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

RIGHE = [
    "La consegna dei materiali e' avvenuta il 12 gennaio, a Bologna, in tre lotti.",
    "Il sopralluogo si e' svolto il 5 febbraio, a Modena, con due tecnici.",
    "La verifica strutturale e' stata eseguita il 19 febbraio, a Parma, su quattro pilastri.",
    "{RIGA}",  # <- la riga sotto misura, in quarta posizione
    "La relazione e' stata depositata il 2 aprile, a Ferrara, in cinque copie.",
    "Il pagamento e' stato disposto il 15 aprile, a Ravenna, in due rate.",
]
#: (parola, riga della fonte, claim vero costruito da quella riga)
PAROLE = [
    ("collaudo",   "Il collaudo si e' concluso il 28 marzo, a Rimini, dopo sei prove.",
                   "Il collaudo si e' concluso il 28 marzo."),
    ("esame",      "L'esame si e' concluso il 28 marzo, a Rimini, dopo sei prove.",
                   "L'esame si e' concluso il 28 marzo."),
    ("controllo",  "Il controllo si e' concluso il 28 marzo, a Rimini, dopo sei prove.",
                   "Il controllo si e' concluso il 28 marzo."),
    ("prova",      "La prova si e' conclusa il 28 marzo, a Rimini, dopo sei prove.",
                   "La prova si e' conclusa il 28 marzo."),
    ("ispezione",  "L'ispezione si e' conclusa il 28 marzo, a Rimini, dopo sei prove.",
                   "L'ispezione si e' conclusa il 28 marzo."),
    ("revisione",  "La revisione si e' conclusa il 28 marzo, a Rimini, dopo sei prove.",
                   "La revisione si e' conclusa il 28 marzo."),
    ("montaggio",  "Il montaggio si e' concluso il 28 marzo, a Rimini, dopo sei prove.",
                   "Il montaggio si e' concluso il 28 marzo."),
    ("trasporto",  "Il trasporto si e' concluso il 28 marzo, a Rimini, dopo sei prove.",
                   "Il trasporto si e' concluso il 28 marzo."),
]


def _fonte(riga: str, posizione: int = 3) -> str:
    righe = [r for r in RIGHE if r != "{RIGA}"]
    righe.insert(posizione, riga)
    return "Registro di cantiere. " + " ".join(righe)


def main() -> int:
    from verimem.client import Memory  # noqa: PLC0415

    mem = Memory(str(Path(tempfile.mkdtemp()) / "parola.db"))

    print("\n  === H1 · LESSICALE: otto parole nella STESSA posizione (quarta riga) ===")
    print(f"  {'parola':<12} {'esito':<12} {'ground':>7}")
    print("  " + "-" * 36)
    caduti_h1 = []
    for parola, riga, claim in PAROLE:
        fonte = _fonte(riga)
        if claim.rstrip(".") not in fonte:  # controllo: il claim e' davvero nella fonte
            print(f"  CONTROLLO CADUTO su «{parola}»: il claim non e' nella sua fonte")
            return 1
        ric = mem.add(claim, topic=f"parola/{parola}", source=fonte, validate="full")
        stato, g = str(ric.get("status")), float(ric.get("grounding_score") or -1)
        if stato == "quarantined":
            caduti_h1.append(parola)
        print(f"  {parola:<12} {'🔴 FERMATO' if stato == 'quarantined' else '🟢 passa':<12} {g:7.2f}")

    print("\n  === H2 · POSIZIONALE: la parola «collaudo» in SEI posizioni diverse ===")
    print(f"  {'posizione':<12} {'esito':<12} {'ground':>7}")
    print("  " + "-" * 36)
    riga_c, claim_c = PAROLE[0][1], PAROLE[0][2]
    caduti_h2 = []
    for pos in range(6):
        fonte = _fonte(riga_c, pos)
        ric = mem.add(claim_c, topic=f"posizione/{pos}", source=fonte, validate="full")
        stato, g = str(ric.get("status")), float(ric.get("grounding_score") or -1)
        if stato == "quarantined":
            caduti_h2.append(pos)
        print(f"  {pos + 1}a di 6      {'🔴 FERMATO' if stato == 'quarantined' else '🟢 passa':<12} {g:7.2f}")

    print("\n  " + "=" * 70)
    print(f"  H1 lessicale:  caduti {len(caduti_h1)}/8  {caduti_h1 or ''}")
    print(f"  H2 posizione:  caduti {len(caduti_h2)}/6  posizioni {caduti_h2 or ''}")
    if caduti_h1 == ["collaudo"] and len(caduti_h2) == 6:
        print("  ⇒ E' LA PAROLA: cade solo «collaudo», e cade in TUTTE le posizioni.")
    elif len(caduti_h1) == 8:
        print("  ⇒ NON e' la parola: cadono tutte ⇒ e' il banco o la struttura della frase.")
    elif not caduti_h1:
        print("  ⇒ NON SI RIPRODUCE: nemmeno «collaudo» cade qui. Il caso precedente"
              " dipendeva da altro nella fonte.")
    else:
        print("  ⇒ Quadro misto: leggere le due tabelle, non il conteggio.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
