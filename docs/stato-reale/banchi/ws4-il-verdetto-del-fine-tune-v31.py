# -*- coding: utf-8 -*-
"""IL VERDETTO del fine-tune v3.1 — e il controllo su astensioni false MAI VISTE.

🔴 UN ERRORE CHE STAVO PER FARE E CHE MI FERMO DA SOLA: le 100 astensioni FALSE
del dataset stanno nel TRAIN. Misurare li' il controllo «ne ferma >= 80%»
misurerebbe la MEMORIZZAZIONE, non la generalizzazione — il modello quelle le ha
viste. Il controllo vale solo su esempi MAI VISTI.

⇒ ne costruisco 100 NUOVE da `squad_v2_dev.jsonl`: documenti che RISPONDONO alla
domanda (e' il dev answerable, mai usato per le astensioni false, che vengono da
`halueval_qa_dev`), con la stessa forma di astensione. Il claim e' FALSO perche'
il documento risponde. Nessuno di questi e' passato dall'addestramento.

PREDIZIONE, depositata il 02/09 in W7-130 e non riscritta:
  veri persi 29,3% → 21-26% · falsita' ammessa ≤18% · FALSIFICATA se veri persi
  ≥27% o falsita' >18% · e sulle astensioni FALSE ≥80%, sotto il 50% ha imparato
  la stringa.
"""
import io
import json
import os
import random
from pathlib import Path

# la cartella dei dati: relativa al repo per default (e' dove il banco
# `ws4-le-astensioni-erano-gia-nel-repo.py` scrive), sovrascrivibile.
SC = os.environ.get("WS4_OUT", "docs/stato-reale/banchi/_out/")
E = "benchmark/data/external/"

nuovi = [json.loads(x) for x in io.open(SC + "punteggi_v31.jsonl", encoding="utf-8")
         if x.strip()]
vecchi = {json.loads(x)["i"]: json.loads(x)
          for x in io.open(SC + "wt_base/punteggi_heldout.jsonl", encoding="utf-8")
          if x.strip()}

veri = [r for r in nuovi if r["label"] == 1]
falsi = [r for r in nuovi if r["label"] == 0]
print(f"  600 claim: veri {len(veri)} · falsi {len(falsi)}")

# ── ① il confronto a PARI VERI PERSI (88/300 = 29,3% del gate attuale) ──
BERS = 88
ordv = sorted(veri, key=lambda r: r["p"])
s = ordv[BERS - 1]["p"] + 1e-12
ff = sum(1 for r in falsi if r["p"] < s)
print(f"\n  ① A PARI VERI PERSI ({BERS}/300 = 29,3%)")
print(f"     il moat ATTUALE ferma  260/300 = 86,7% dei falsi")
print(f"     il moat v3.1 ferma     {ff}/300 = {100*ff/300:.1f}%"
      f"   ({100*ff/300 - 86.7:+.1f} punti)")

# ── ② il numero della PREDIZIONE: a pari FALSITA' AMMESSA ───────────────
# il gate attuale ammette 40/300 = 13,3% dei falsi. A quella soglia, quanti
# veri perde il modello nuovo?
ordf = sorted(falsi, key=lambda r: r["p"])
s2 = ordf[260 - 1]["p"] + 1e-12          # la soglia che ferma 260 falsi
vp = sum(1 for r in veri if r["p"] < s2)
print(f"\n  ② A PARI FALSI FERMATI (260/300 = 86,7%, falsita' ammessa 13,3%)")
print(f"     il moat ATTUALE perde  84/300 = 28,0% dei veri")
print(f"     il moat v3.1 perde     {vp}/300 = {100*vp/300:.1f}%"
      f"   ({100*vp/300 - 28.0:+.1f} punti)")

# ── ③ IL CONTROLLO: astensioni FALSE mai viste ──────────────────────────
import torch  # noqa: E402
from transformers import (AutoModelForSequenceClassification,  # noqa: E402
                          AutoTokenizer)

OUT = Path(SC) / "ce_v31"
tok = AutoTokenizer.from_pretrained(str(OUT))
mod = AutoModelForSequenceClassification.from_pretrained(str(OUT))
mod.eval()

FORME = ["The document does not say.",
         "That is not stated in the passage.",
         "There is no information about that in this text.",
         "The passage does not answer that.",
         "This source does not contain that information."]
sq = [json.loads(x) for x in io.open(E + "squad_v2_dev.jsonl", encoding="utf-8")
      if x.strip()]
rng = random.Random(23)
prove = [(r["knowledge"], f"{r['question']} {rng.choice(FORME)}") for r in sq]
print(f"\n  ③ IL CONTROLLO — {len(prove)} astensioni FALSE mai viste"
      f" (da squad_v2_dev: documenti che RISPONDONO, e le astensioni false del"
      f" train venivano da halueval_qa_dev)")
pf = []
with torch.no_grad():
    for i in range(0, len(prove), 16):
        lotto = prove[i:i + 16]
        enc = tok([a for a, _ in lotto], [b for _, b in lotto],
                  truncation="longest_first", max_length=512,
                  padding=True, return_tensors="pt")
        pf += torch.sigmoid(mod(**enc).logits.squeeze(-1)).tolist()

for nome, soglia in (("a pari veri persi", s), ("a pari falsi fermati", s2)):
    fermate = sum(1 for p in pf if p < soglia)
    print(f"     {nome} (soglia {soglia:.4f}): ferma {fermate}/{len(pf)}"
          f" = {100*fermate/len(pf):.1f}% delle astensioni false")

fermate = sum(1 for p in pf if p < s)
q = 100 * fermate / len(pf)
print("\n  == I VERDETTI, contro la predizione depositata il 02/09 ==")
pv = 100 * vp / 300
print(f"     veri persi 21-26%:        {'REGGE' if 21 <= pv <= 26 else 'FALSIFICATA'}"
      f"   ({pv:.1f}%)")
print(f"     FALSIFICATA se >= 27%:    {'SI' if pv >= 27 else 'no'}")
print(f"     astensioni false >= 80%:  {'REGGE' if q >= 80 else 'FALSIFICATA'}"
      f"   ({q:.1f}%)")
print(f"     ha imparato la STRINGA (<50%)?  {'SI — il guadagno non vale' if q < 50 else 'no'}")
