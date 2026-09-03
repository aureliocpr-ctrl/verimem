# -*- coding: utf-8 -*-
"""LA COLONNA CHE MANCA alla tabella della zavorra: il giudice RIFINITO da me.

🔑 MEMORIA-FIRST, e mi ha risparmiato un esperimento intero. Prima di lanciare
un confronto a tre modelli ho cercato in memoria, e il confronto ESISTE GIA':
  * `878f10c3026b` — «il modello `cross-encoder/nli-deberta-v3-base` risponde
    contradiction con probabilita' 1.00 mentre `local_gate_ce_v2` risponde 1.84,
    99.94 e 99.87»
  * `b23b3296b75c` — MiniCheck risponde 0 (unsupported) con 0.98-0.99
⇒ base, il nostro e MiniCheck sono gia' misurati. **Manca solo il mio `ce_v31`.**
Non rifaccio le tre colonne che ci sono: ne aggiungo una.

⚠️ E LE CELLE NON SONO LE MIE: sono le quattro di @ws3 (`dd91c33a`), e lui ha
scritto perche' servono proprio quelle — «per confrontare MODELLI diversi sulla
zavorra servono le due righe che RIBALTANO, non le trenta coppie», perche' sulle
trenta la zavorra fa 0/30. **Mi aveva corretto la premessa prima che spendessi
lo slot.**

LA DOMANDA: il mio fine-tune ha PEGGIORATO la capacita' che il base aveva?
  base OK · v2 no · v31 no      il danno e' del PRIMO fine-tune
  base OK · v2 no · v31 PEGGIO  i danni si SOMMANO
  base OK · v2 no · v31 OK      il mio training ha per caso riparato

⚠️ QUATTRO CELLE SONO QUATTRO CELLE: qualunque cosa esca, e' un indizio, non una
misura. Lo scrivo qui perche' nella cella non diventi altro.
"""
import os

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from pathlib import Path

# il modello rifinito: passato per variabile, con un default nel repo.
# Il modello NON e' versionato (700 MB): si rigenera col banco
# `ws4-il-fine-tune-v31-del-giudice.py`.
SC = os.environ.get("WS4_OUT", "docs/stato-reale/banchi/_out/")

FONTE = "Verbale: il direttore ha rassegnato le dimissioni il 4 maggio."
ZAVORRA = "La mensa aziendale resta chiusa il primo maggio."
CLAIM = [
    ("confermato, e' con apostrofo",
     "Il direttore e' stato confermato nell'incarico il 4 maggio."),
    ("confermato, e nuda",
     "Il direttore e stato confermato nell'incarico il 4 maggio."),
    ("in carica,  e' con apostrofo",
     "Il direttore e' ancora in carica il 4 maggio."),
    ("in carica,  e nuda",
     "Il direttore e ancora in carica il 4 maggio."),
]
# tutti e quattro i claim sono FALSI: la fonte dice che si e' dimesso.
CELLE = []
for nome, c in CLAIM:
    CELLE.append((nome + " | fonte nuda", FONTE, c))
    CELLE.append((nome + " | + zavorra", FONTE + " " + ZAVORRA, c))

MODELLI = [
    ("base", "cross-encoder/nli-deberta-v3-base"),
    ("v2 (nostro)", str(Path.home() / ".engram" / "models" / "local_gate_ce_v2")),
    ("v31 (mio)", SC + "ce_v31"),
]

print(f"  {len(CELLE)} celle · {len(MODELLI)} modelli\n")
ris = {}
for nome, path in MODELLI:
    try:
        tok = AutoTokenizer.from_pretrained(path)
        mod = AutoModelForSequenceClassification.from_pretrained(path)
    except Exception as exc:  # noqa: BLE001
        print(f"  ⚠️ {nome}: non caricabile ({str(exc)[:50]})")
        continue
    mod.eval()
    p = []
    with torch.no_grad():
        for _, src, cl in CELLE:
            enc = tok(src, cl, truncation="longest_first", max_length=512,
                      return_tensors="pt")
            out = mod(**enc).logits
            if out.shape[-1] == 1:
                p.append(float(torch.sigmoid(out.squeeze(-1))))
            else:
                # 3 vie: prendo la probabilita' di ENTAILMENT (indice 1)
                p.append(float(torch.softmax(out, dim=-1)[0][1]))
    ris[nome] = p
    print(f"  {nome:<14} caricato")

nomi = list(ris)
print(f"\n  {'cella':<36} " + " ".join(f"{n:>13}" for n in nomi))
for k, (nome, _, _) in enumerate(CELLE):
    print(f"  {nome:<36} " + " ".join(f"{ris[n][k]:>13.3f}" for n in nomi))

print("\n  == L'EFFETTO DELLA ZAVORRA, per modello ==")
print("     (quanto sale il punteggio aggiungendo la frase estranea)")
for n in nomi:
    salti = [ris[n][2 * i + 1] - ris[n][2 * i] for i in range(len(CLAIM))]
    peggio = max(salti)
    print(f"     {n:<14} salti {[round(s, 3) for s in salti]}"
          f"  · massimo {peggio:+.3f}")
print("\n  ⚠️ quattro claim in due regimi: un INDIZIO, non una misura.")
