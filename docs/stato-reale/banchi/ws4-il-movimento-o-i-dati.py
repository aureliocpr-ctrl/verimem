# -*- coding: utf-8 -*-
"""IL CONFONDENTE: basta MUOVERE i pesi, o servono dati sensati?

La domanda nasce da due misure mie: il v31 (fonti lunghe) e il v31-corto (fonti
di una frase) **resistono entrambi** alla zavorra (+0,031 e +0,083) mentre il v2
crolla (+0,990). Il fattore comune fra i due che resistono non e' il contenuto
del dataset — quello l'ho gia' falsificato accorciando le fonti — ma il fatto
stesso di essere stati **riaddestrati**.

⇒ se e' cosi', **ogni nostra tabella a tre modelli ha dentro un confondente**:
confrontare `base`, `v2` e `v31` non dice solo «cosa ha imparato chi», dice
anche «chi e' stato toccato per ultimo». Nessuno l'aveva nominato, la mia
compresa.

IL DISEGNO che lo separa: stesso dataset, stesso seme, stessi 212 passi, ma con
le **ETICHETTE MESCOLATE A CASO**. Un modello addestrato su etichette casuali
non puo' imparare NIENTE di sensato: se la zavorra si ripara lo stesso, e' il
movimento dei pesi; se non si ripara, servono dati veri.

🔮 PREDIZIONE, scritta prima (03/09 21:41):
  · il modello a etichette casuali RIPARA lo stesso: effetto zavorra < 0,3
  · FALSIFICATA se l'effetto resta >= 0,5 (cioe' vicino al v2, +0,990)
  ⚠️ CONTROLLO OBBLIGATORIO: con etichette casuali il modello NON deve separare
     vero da falso (differenza < 0,3 sulla cella nuda). Se separa, le etichette
     non erano casuali e il banco misura un'altra cosa.
"""
import io
import json
import os
import random
import time
from pathlib import Path

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

# i dati e la cartella di uscita: relativi al repo per default.
SC = os.environ.get("WS4_OUT", "docs/stato-reale/banchi/_out/")
OUT = Path(SC) / "ce_casuale"
BASE = Path.home() / ".engram" / "models" / "local_gate_ce_v2"
SEED, BATCH, EPOCHE, LR, MAXLEN = 7, 8, 2, 2e-5, 512

righe = []
for f in (SC + "v3_train.jsonl", SC + "v31_astensioni.jsonl"):
    for x in io.open(f, encoding="utf-8"):
        if x.strip():
            righe.append(json.loads(x))

rng = random.Random(SEED)
etichette = [r["label"] for r in righe]
rng.shuffle(etichette)                      # ← L'UNICA VARIABILE
uguali = sum(1 for r, e in zip(righe, etichette) if r["label"] == e)
for r, e in zip(righe, etichette):
    r["label"] = e
print(f"  {len(righe)} esempi · etichette MESCOLATE"
      f" (coincidono per caso: {uguali} = {100*uguali/len(righe):.0f}%)")

train = righe
tok = AutoTokenizer.from_pretrained(str(BASE))
model = AutoModelForSequenceClassification.from_pretrained(
    str(BASE), num_labels=1, ignore_mismatched_sizes=True)
model.train()
opt = torch.optim.AdamW(model.parameters(), lr=LR)
passi = ((len(train) + BATCH - 1) // BATCH) * EPOCHE
sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=LR, total_steps=passi,
                                            pct_start=0.1)
perdita = torch.nn.BCEWithLogitsLoss()
print(f"  addestro {passi} passi (identici al v31)")
t0 = time.time()
for ep in range(EPOCHE):
    ordine = list(range(len(train)))
    rng.shuffle(ordine)
    tot, nb = 0.0, 0
    for i in range(0, len(ordine), BATCH):
        lotto = [train[j] for j in ordine[i:i + BATCH]]
        enc = tok([b["source"] for b in lotto], [b["claim"] for b in lotto],
                  truncation="longest_first", max_length=MAXLEN,
                  padding=True, return_tensors="pt")
        y = torch.tensor([float(b["label"]) for b in lotto])
        loss = perdita(model(**enc).logits.squeeze(-1), y)
        loss.backward()
        opt.step()
        sched.step()
        opt.zero_grad()
        tot += float(loss.detach())
        nb += 1
        if nb % 50 == 0:
            print(f"    ep{ep} passo {nb} perdita {tot/nb:.4f}"
                  f" ({time.time()-t0:.0f}s)", flush=True)
    print(f"  epoca {ep}: perdita {tot/max(1,nb):.4f}"
          f"   (su etichette casuali NON deve scendere molto)")
OUT.mkdir(parents=True, exist_ok=True)
model.save_pretrained(OUT)
tok.save_pretrained(OUT)
print(f"  addestrato in {time.time()-t0:.0f}s")

model.eval()
F = "Verbale: il direttore ha rassegnato le dimissioni il 4 maggio."
Z = "La mensa aziendale resta chiusa il primo maggio."
VERO = "Il direttore ha rassegnato le dimissioni il 4 maggio."
FALSI = ["Il direttore e' stato confermato nell'incarico il 4 maggio.",
         "Il direttore e stato confermato nell'incarico il 4 maggio.",
         "Il direttore e' ancora in carica il 4 maggio.",
         "Il direttore e ancora in carica il 4 maggio."]


def p(src, cl):
    with torch.no_grad():
        return float(torch.sigmoid(model(**tok(
            src, cl, truncation="longest_first", max_length=MAXLEN,
            return_tensors="pt")).logits.squeeze(-1)))


sep = p(F, VERO) - p(F, FALSI[0])
print(f"\n  CONTROLLO — separa vero da falso? {sep:+.3f}"
      f"   {'ACCESO (NON separa, come deve essere)' if abs(sep) < 0.3 else 'SPENTO: separa, le etichette non erano casuali'}")
salti = [p(F + " " + Z, c) - p(F, c) for c in FALSI]
eff = max(salti)
print(f"\n  effetto della zavorra, modello a ETICHETTE CASUALI:"
      f" {[round(s,3) for s in salti]}")
print(f"    massimo {eff:+.3f}")
print(f"    [v2 nostro +0,990 · v31 +0,031 · v31-corto +0,083]")
print("\n  == IL VERDETTO ==")
if abs(sep) >= 0.3:
    print("     non leggibile: il controllo e' spento")
elif eff < 0.3:
    print(f"     E' IL MOVIMENTO: con etichette CASUALI la zavorra si ripara")
    print(f"     lo stesso ({eff:+.3f}) ⇒ il difetto del v2 e' fragile, e OGNI")
    print("     nostro confronto fra modelli ha dentro «chi e' stato toccato")
    print("     per ultimo». La predizione REGGE.")
elif eff >= 0.5:
    print(f"     SERVONO DATI SENSATI: con etichette casuali l'effetto resta")
    print(f"     {eff:+.3f} ⇒ la mia predizione e' FALSIFICATA e il v31 ha")
    print("     imparato qualcosa di specifico.")
else:
    print(f"     IN MEZZO ({eff:+.3f}): quattro celle non bastano a decidere.")
