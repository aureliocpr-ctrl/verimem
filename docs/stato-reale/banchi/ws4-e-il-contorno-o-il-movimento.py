# -*- coding: utf-8 -*-
"""FALSIFICO LA MIA IPOTESI: e' il CONTORNO lungo che ha insegnato al v31 a
resistere alla zavorra?

In W7-135 ho scritto: *«il mio dataset e' fatto di `knowledge` di SQuAD e
HaluEval, paragrafi lunghi con molto testo irrilevante intorno al fatto — che e'
esattamente la forma della zavorra ⇒ il modello potrebbe aver imparato a
IGNORARE IL CONTORNO. Si falsifica addestrando lo stesso dataset con fonti
ACCORCIATE a una frase: se la resistenza sparisce, l'ipotesi regge.»*

Eccolo. **Una variabile sola**: stesso dataset, stesso seme, stessi
iperparametri, stesso numero di passi — cambia SOLO la lunghezza della fonte.

🔮 PREDIZIONE, scritta prima di eseguire (03/09 20:55):
  · il modello addestrato su fonti CORTE avra' un effetto-zavorra ALTO —
    fra +0,3 e +0,99, cioe' vicino al nostro v2 (+0,990) e lontano dal v31
    (+0,031)
  · FALSIFICATA se l'effetto resta sotto +0,15: allora la resistenza NON viene
    dal contorno lungo, e la mia spiegazione e' sbagliata
  · CONTROLLO OBBLIGATORIO: il modello corto deve comunque SEPARARE vero da
    falso sulla fonte nuda (>= +0,5). Se non separa, non ha imparato niente e
    l'effetto-zavorra non si puo' leggere.
"""
import io
import json
import os
import random
import re
import time
from pathlib import Path

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

SC = os.environ.get("WS4_OUT", "docs/stato-reale/banchi/_out/")
OUT = Path(SC) / "ce_v31_corto"
BASE = Path.home() / ".engram" / "models" / "local_gate_ce_v2"
SEED, BATCH, EPOCHE, LR, MAXLEN = 7, 8, 2, 2e-5, 512


def prima_frase(t: str) -> str:
    """La fonte accorciata: la prima frase, che e' l'unica variabile."""
    parti = re.split(r"(?<=[.!?])\s+", (t or "").strip())
    return parti[0] if parti else (t or "")


righe = []
for f in (SC + "v3_train.jsonl", SC + "v31_astensioni.jsonl"):
    for x in io.open(f, encoding="utf-8"):
        if x.strip():
            r = json.loads(x)
            r["source"] = prima_frase(r["source"])
            righe.append(r)

lung = [len(r["source"]) for r in righe]
print(f"  {len(righe)} esempi · lunghezza media della fonte ACCORCIATA:"
      f" {sum(lung)/len(lung):.0f} caratteri")

rng = random.Random(SEED)
strati = {}
for r in righe:
    strati.setdefault((r.get("fonte", "?"), r["label"]), []).append(r)
train, val = [], []
for _, g in sorted(strati.items()):
    rng.shuffle(g)
    n = max(1, int(round(len(g) * 0.10)))
    val += g[:n]
    train += g[n:]
print(f"  train {len(train)} · val {len(val)}  (stesso seme e stessa quota del v31)")

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
        if nb % 40 == 0:
            print(f"    ep{ep} passo {nb} perdita {tot/nb:.4f}"
                  f" ({time.time()-t0:.0f}s)", flush=True)
    print(f"  epoca {ep}: perdita {tot/max(1,nb):.4f}")
OUT.mkdir(parents=True, exist_ok=True)
model.save_pretrained(OUT)
tok.save_pretrained(OUT)
print(f"  addestrato in {time.time()-t0:.0f}s")

# ── la misura: le stesse quattro celle di @ws3 ──────────────────────────
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
print(f"\n  CONTROLLO — separa VERO da FALSO sulla fonte nuda: {sep:+.3f}"
      f"   {'ACCESO' if sep >= 0.5 else 'SPENTO: non ha imparato, non leggere sotto'}")
salti = [p(F + " " + Z, c) - p(F, c) for c in FALSI]
eff = max(salti)
print(f"\n  effetto della zavorra sul modello CORTO: {[round(s,3) for s in salti]}")
print(f"    massimo {eff:+.3f}")
print(f"    [v31 fonti lunghe: +0,031 · v2 nostro: +0,990]")
print("\n  == IL VERDETTO ==")
if sep < 0.5:
    print("     non leggibile: il controllo e' spento")
elif eff >= 0.3:
    print(f"     L'IPOTESI REGGE: con fonti corte l'effetto risale a {eff:+.3f}")
    print("     ⇒ e' il CONTORNO lungo del dataset che insegna a ignorarlo.")
elif eff < 0.15:
    print(f"     IPOTESI FALSIFICATA: l'effetto resta {eff:+.3f} anche con fonti")
    print("     corte ⇒ la resistenza NON viene dal contorno. La mia")
    print("     spiegazione di W7-135 e' sbagliata e va ritirata.")
else:
    print(f"     IN MEZZO ({eff:+.3f}): l'ipotesi non e' ne' confermata ne'")
    print("     falsificata da quattro celle. Serve una popolazione.")
