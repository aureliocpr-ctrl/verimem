# -*- coding: utf-8 -*-
"""E' LA DATA A FAR CADERE UN CLAIM VERO? — la variabile isolata

PERCHE' ESISTE. Il banco `ws7-i-veri-cadono-in-italiano.py` ha falsificato il
sospetto sulla lingua (2 veri fermati su 10 in italiano, 2 su 10 in inglese) ma
ha lasciato un pattern che il totale nascondeva: **tre dei quattro claim VERI
fermati citavano una DATA TESTUALE**, tutti con grounding >= 99,97.

    «I lavori si sono conclusi il 28 marzo.»          IT  99.98  FERMATO
    «The works started on 12 January.»                EN  99.97  FERMATO
    «The works ended on 28 March.»                    EN  99.97  FERMATO

Tre casi non sono una causa. Questo banco isola la variabile.

COME. Sei schemi di frase, ognuno declinato con **tre tipi di complemento**
diversi e nient'altro di diverso:

    DATA      «La consegna e' avvenuta il 12 gennaio.»
    LUOGO     «La consegna e' avvenuta a Bologna.»
    QUANTITA' «La consegna e' avvenuta in tre lotti.»

Stesso verbo, stessa struttura, stessa fonte, tutti VERI e tutti letteralmente
sostenuti. Se a cadere sono le date e non gli altri due, la variabile e'
isolata; se cadono in modo simile, il pattern del banco precedente era un caso
e va detto.

LE DUE POPOLAZIONI: accanto ai 18 veri ci sono 3 FALSI (una data sbagliata, un
luogo sbagliato, una quantita' sbagliata) che DEVONO essere fermati. Se non lo
fossero il gate sarebbe spento e il conto sui veri non direbbe niente.

    python docs/stato-reale/banchi/ws7-la-data-fa-cadere-il-vero.py

Store TEMPORANEO via `HIPPO_DATA_DIR`. Fuori da pytest.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from collections import Counter

FONTE = (
    "Registro di cantiere. La consegna dei materiali e' avvenuta il 12 gennaio, a Bologna, "
    "in tre lotti. Il sopralluogo si e' svolto il 5 febbraio, a Modena, con due tecnici. "
    "La verifica strutturale e' stata eseguita il 19 febbraio, a Parma, su quattro pilastri. "
    "Il collaudo si e' concluso il 28 marzo, a Rimini, dopo sei prove. La relazione e' stata "
    "depositata il 2 aprile, a Ferrara, in cinque copie. Il pagamento e' stato disposto il "
    "15 aprile, a Ravenna, in due rate."
)

#: (schema, complemento DATA, complemento LUOGO, complemento QUANTITA')
SCHEMI = [
    ("consegna",  "La consegna dei materiali e' avvenuta il 12 gennaio.",
                  "La consegna dei materiali e' avvenuta a Bologna.",
                  "La consegna dei materiali e' avvenuta in tre lotti."),
    ("sopralluogo", "Il sopralluogo si e' svolto il 5 febbraio.",
                  "Il sopralluogo si e' svolto a Modena.",
                  "Il sopralluogo si e' svolto con due tecnici."),
    ("verifica",  "La verifica strutturale e' stata eseguita il 19 febbraio.",
                  "La verifica strutturale e' stata eseguita a Parma.",
                  "La verifica strutturale e' stata eseguita su quattro pilastri."),
    ("collaudo",  "Il collaudo si e' concluso il 28 marzo.",
                  "Il collaudo si e' concluso a Rimini.",
                  "Il collaudo si e' concluso dopo sei prove."),
    ("relazione", "La relazione e' stata depositata il 2 aprile.",
                  "La relazione e' stata depositata a Ferrara.",
                  "La relazione e' stata depositata in cinque copie."),
    ("pagamento", "Il pagamento e' stato disposto il 15 aprile.",
                  "Il pagamento e' stato disposto a Ravenna.",
                  "Il pagamento e' stato disposto in due rate."),
]

FALSI = [
    ("data",      "La consegna dei materiali e' avvenuta il 30 novembre."),
    ("luogo",     "La consegna dei materiali e' avvenuta a Napoli."),
    ("quantita",  "La consegna dei materiali e' avvenuta in nove lotti."),
]


def main() -> int:
    # Controllo che DEVE poter fallire: i dati falsi non sono nella fonte, i veri si'.
    for tok in ("30 novembre", "Napoli", "nove lotti"):
        if tok in FONTE:
            print(f"  CONTROLLO CADUTO: «{tok}» e' nella fonte")
            return 1
    print(f"  controllo retto: {len(SCHEMI)} schemi x 3 tipi = {len(SCHEMI) * 3} claim VERI, "
          f"{len(FALSI)} falsi, e i dati inventati non sono nella fonte\n")

    from verimem.client import Memory  # noqa: PLC0415

    mem = Memory(str(Path(tempfile.mkdtemp()) / "date.db"))
    fermati = Counter()
    print(f"  {'schema':<12} {'DATA':<22} {'LUOGO':<22} QUANTITA'")
    print("  " + "-" * 76)
    for schema, *varianti in SCHEMI:
        celle = []
        for tipo, claim in zip(("data", "luogo", "quantita"), varianti):
            ric = mem.add(claim, topic=f"date/{schema}/{tipo}", source=FONTE, validate="full")
            stato = str(ric.get("status"))
            g = float(ric.get("grounding_score") or -1)
            if stato == "quarantined":
                fermati[tipo] += 1
            celle.append(f"{'🔴 FERMATO' if stato == 'quarantined' else '🟢 passa':<11}{g:6.2f}")
        print(f"  {schema:<12} {celle[0]:<22} {celle[1]:<22} {celle[2]}")

    passati_falsi = []
    for tipo, claim in FALSI:
        ric = mem.add(claim, topic=f"date/falso/{tipo}", source=FONTE, validate="full")
        if str(ric.get("status")) != "quarantined":
            passati_falsi.append(tipo)

    n = len(SCHEMI)
    print("\n  " + "=" * 76)
    print(f"  VERI FERMATI:  data {fermati['data']}/{n} · luogo {fermati['luogo']}/{n} · "
          f"quantita {fermati['quantita']}/{n}")
    print(f"  controllo:     falsi passati {len(passati_falsi)}/{len(FALSI)} {passati_falsi or ''}"
          "  (se non e' 0, il gate e' spento e il conto sopra non significa niente)")
    if fermati["data"] > max(fermati["luogo"], fermati["quantita"]):
        print("  ⇒ LA DATA CADE PIU' DEGLI ALTRI DUE: variabile isolata su questo corpus.")
    elif fermati["data"] == fermati["luogo"] == fermati["quantita"]:
        print("  ⇒ NESSUNA DIFFERENZA fra i tre tipi: il pattern precedente era un caso.")
    else:
        print("  ⇒ La data NON e' il tipo che cade di piu': ipotesi da riscrivere.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
