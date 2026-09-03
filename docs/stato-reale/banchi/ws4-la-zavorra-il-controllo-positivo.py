# -*- coding: utf-8 -*-
"""IL CONTROLLO POSITIVO che mancava al confronto sulla zavorra.

Il mio `ce_v31` da' punteggi bassissimi su tutte e quattro le celle (0,029-0,086)
e quindi «resiste alla zavorra» (salto massimo +0,031 contro +0,990 del nostro
v2). Ma un modello che da' BASSO A TUTTO resiste a qualunque cosa senza sapere
niente: il salto piccolo sarebbe un artefatto della taratura, non una capacita'.

⇒ serve un claim VERO sulla stessa fonte. Se il v31 gli da' ALTO, discrimina e
il confronto vale; se gli da' basso come ai falsi, non discrimina e il «+0,031»
non significa nulla.
"""
import os

import torch
from pathlib import Path

from transformers import AutoModelForSequenceClassification, AutoTokenizer

# il modello rifinito: passato per variabile, con un default nel repo.
# Il modello NON e' versionato (700 MB): si rigenera col banco
# `ws4-il-fine-tune-v31-del-giudice.py`.
SC = os.environ.get("WS4_OUT", "docs/stato-reale/banchi/_out/")

F = "Verbale: il direttore ha rassegnato le dimissioni il 4 maggio."
Z = "La mensa aziendale resta chiusa il primo maggio."
VERO = "Il direttore ha rassegnato le dimissioni il 4 maggio."
FALSO = "Il direttore e' stato confermato nell'incarico il 4 maggio."
CELLE = [("VERO nudo", F, VERO), ("VERO +zavorra", F + " " + Z, VERO),
         ("FALSO nudo", F, FALSO), ("FALSO +zavorra", F + " " + Z, FALSO)]
MODELLI = [("base", "cross-encoder/nli-deberta-v3-base"),
           ("v2", str(Path.home() / ".engram" / "models" / "local_gate_ce_v2")),
           ("v31", SC + "ce_v31")]

ris = {}
for nome, path in MODELLI:
    tok = AutoTokenizer.from_pretrained(path)
    mod = AutoModelForSequenceClassification.from_pretrained(path)
    mod.eval()
    v = []
    with torch.no_grad():
        for _, s, c in CELLE:
            o = mod(**tok(s, c, truncation="longest_first", max_length=512,
                          return_tensors="pt")).logits
            v.append(float(torch.sigmoid(o.squeeze(-1))) if o.shape[-1] == 1
                     else float(torch.softmax(o, dim=-1)[0][1]))
    ris[nome] = v

print(f"  {'cella':<18} " + " ".join(f"{n:>9}" for n, _ in MODELLI))
for k, (nm, _, _) in enumerate(CELLE):
    print(f"  {nm:<18} " + " ".join(f"{ris[n][k]:>9.3f}" for n, _ in MODELLI))
print()
for n, _ in MODELLI:
    d = ris[n][0] - ris[n][2]
    print(f"  {n:<5} separa VERO da FALSO (fonte nuda): {d:+.3f}"
          f"   {'DISCRIMINA' if d > 0.2 else 'NON discrimina'}")
