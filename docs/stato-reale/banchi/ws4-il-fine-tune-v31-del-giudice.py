# -*- coding: utf-8 -*-
"""FINE-TUNE v3.1 — il giudice riaddestrato sulle astensioni, con la predizione
gia' depositata e il controllo che dice se ha imparato la RELAZIONE o la FORMA.

PREDIZIONE DEPOSITATA IL 02/09 (cella W7-130), non riscritta adesso:
  · veri persi da 29,3% a FRA il 21% e il 26%
  · e la falsita' ammessa NON supera il 18%
  · tetto strutturale: solo 73 degli 88 veri persi passano dal moat ⇒ sotto il
    19,7% non si scende curando il solo giudice
  · FALSIFICATA se i veri persi restano >= 27% OPPURE la falsita' ammessa > 18%
  🎯 IL CONTROLLO CHE DECIDE SE HA IMPARATO LA RELAZIONE O LA FORMA: sulle
     astensioni FALSE (stessa forma, ma su documenti che RISPONDONO) il modello
     deve fermarne >= 80%. SOTTO IL 50% ha imparato la stringa «forma di
     astensione => vero» e il guadagno sui veri non vale niente.

⛔ NON TOCCA IL MODELLO DI PRODUZIONE: addestra a partire da `local_gate_ce_v2`
e salva in una cartella dello scratchpad. La valutazione carica il modello nuovo
per percorso — `ENGRAM_LOCAL_GATE_MODEL` non viene esportata a nessuno.

CONTROLLI CHE DEVONO ACCENDERSI, in quest'ordine:
  ① il modello base esiste e si carica (senza, il resto e' aria)
  ② la VAL non e' vuota e non e' tutta di una classe
  ③ il modello NUOVO produce punteggi diversi da quello vecchio: se sono
     identici l'addestramento non ha fatto niente e i numeri sotto sono
     quelli di prima con un altro nome
"""
import io
import json
import os
import random
import time
from pathlib import Path

# la cartella dei dati: relativa al repo per default (e' dove il banco
# `ws4-le-astensioni-erano-gia-nel-repo.py` scrive), sovrascrivibile.
SC = os.environ.get("WS4_OUT", "docs/stato-reale/banchi/_out/")
OUT = Path(SC) / "ce_v31"
BASE = Path.home() / ".engram" / "models" / "local_gate_ce_v2"
SEED, BATCH, EPOCHE, LR, MAXLEN = 7, 8, 2, 2e-5, 512

import torch  # noqa: E402
from transformers import (AutoModelForSequenceClassification,  # noqa: E402
                          AutoTokenizer)

print("  ① il modello base c'e'?")
print(f"    {BASE}  esiste={BASE.exists()}")
if not BASE.exists():
    raise SystemExit("    CONTROLLO SPENTO: senza il base non si addestra nulla")

righe = []
for f, fonte in ((SC + "v3_train.jsonl", "v3"),
                 (SC + "v31_astensioni.jsonl", "v3.1")):
    for x in io.open(f, encoding="utf-8"):
        if x.strip():
            r = json.loads(x)
            r["_fonte"] = fonte
            righe.append(r)
print(f"\n  dataset: {len(righe)} esempi"
      f"  (veri {sum(1 for r in righe if r['label'] == 1)})")

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
print(f"  train {len(train)} · val {len(val)}")
print(f"\n  ② la VAL regge? veri {sum(1 for r in val if r['label'] == 1)}"
      f" · falsi {sum(1 for r in val if r['label'] == 0)}")
if not val or len({r["label"] for r in val}) < 2:
    raise SystemExit("    CONTROLLO SPENTO: val vuota o di una sola classe")

tok = AutoTokenizer.from_pretrained(str(BASE))
model = AutoModelForSequenceClassification.from_pretrained(
    str(BASE), num_labels=1, ignore_mismatched_sizes=True)
model.train()
opt = torch.optim.AdamW(model.parameters(), lr=LR)
passi = ((len(train) + BATCH - 1) // BATCH) * EPOCHE
sched = torch.optim.lr_scheduler.OneCycleLR(
    opt, max_lr=LR, total_steps=passi, pct_start=0.1)
perdita = torch.nn.BCEWithLogitsLoss()
print(f"\n  addestro: {passi} passi (batch {BATCH}, {EPOCHE} epoche, lr {LR})")

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
        out = model(**enc).logits.squeeze(-1)
        loss = perdita(out, y)
        loss.backward()
        opt.step()
        sched.step()
        opt.zero_grad()
        tot += float(loss)
        nb += 1
        if nb % 25 == 0:
            print(f"    ep{ep} passo {nb}  perdita {tot/nb:.4f}"
                  f"  ({time.time()-t0:.0f}s)", flush=True)
    print(f"  epoca {ep}: perdita media {tot/max(1,nb):.4f}")

OUT.mkdir(parents=True, exist_ok=True)
model.save_pretrained(OUT)
tok.save_pretrained(OUT)
print(f"  addestrato in {time.time()-t0:.0f}s -> {OUT}")

# ── la valutazione sui 600 di TruthfulQA ────────────────────────────────
model.eval()
E = "benchmark/data/external/truthfulqa_pairs_heldout.jsonl"
test = [json.loads(x) for x in io.open(E, encoding="utf-8") if x.strip()]
print(f"\n  valuto sui {len(test)} di TruthfulQA…")
t0 = time.time()
punti = []
with torch.no_grad():
    for i in range(0, len(test), 16):
        lotto = test[i:i + 16]
        enc = tok([b["source"] for b in lotto], [b["claim"] for b in lotto],
                  truncation="longest_first", max_length=MAXLEN,
                  padding=True, return_tensors="pt")
        s = torch.sigmoid(model(**enc).logits.squeeze(-1)).tolist()
        punti += s if isinstance(s, list) else [s]
        if (i // 16) % 10 == 0:
            print(f"    ...{i+len(lotto)}/{len(test)} ({time.time()-t0:.0f}s)",
                  flush=True)
io.open(SC + "punteggi_v31.jsonl", "w", encoding="utf-8").write(
    chr(10).join(json.dumps({"i": k + 1, "label": r["label"], "p": p})
                 for k, (r, p) in enumerate(zip(test, punti))))
print(f"  valutato in {time.time()-t0:.0f}s")

vecchi = {json.loads(x)["i"]: json.loads(x)
          for x in io.open(SC + "wt_base/punteggi_heldout.jsonl", encoding="utf-8")
          if x.strip()}
diversi = sum(1 for k, p in enumerate(punti, 1)
              if abs(p * 100 - (vecchi.get(k, {}).get("score") or 0)) > 1.0)
print(f"\n  ③ punteggi diversi dal modello vecchio: {diversi}/{len(punti)}"
      f"   {'ACCESO' if diversi > len(punti) * 0.5 else 'SPENTO: ha imparato poco'}")
