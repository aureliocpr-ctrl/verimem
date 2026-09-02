"""T1.1 — FactCG-DeBERTa-v3-Large contro il moat, sui 600 di TruthfulQA.

PREDIZIONE DEPOSITATA PRIMA (canale c753f6d4, 02/09 ~18:00Z):
  · veri persi >= 25%  (oggi 29,3% col moat) e falsi fermati >= 80% (oggi 86,7%)
  · FALSIFICATA se i veri persi scendono sotto il 20%
  · la ricerca predice <20% a falsita' <=18%: una delle due cade
  · ragione: se la classe dominante sono le ASTENSIONI, «I have no comment» non
    e' entailed da nessuna source per NESSUN modello NLI.

LA MAPPATURA DELLE ETICHETTE NON E' DICHIARATA (`id2label: None`) e non la
indovino: la determino DAI DATI. Sui 600 claim l'etichetta vero/falso e' nota,
quindi l'indice «supported» e' quello la cui probabilita' media e' PIU' ALTA sui
veri che sui falsi. Se nessuno dei due separa, il modello non e' utilizzabile e
il banco si ferma.

Su quattro coppie ovvie l'indice 1 vinceva su entrambe le entailed e sulla
contraddizione lessicale netta (Paris/Italy: 0,906 contro 0,094) — ma NON sulla
contraddizione NUMERICA (42 -> 4200 seconds: 0,528 a «supported»). Quel caso e'
riportato qui perche' e' un dato in se': il nostro moat lo prende (score 0,72 su
100, cella W7-112).

CONTROLLI CHE DEVONO ACCENDERSI:
  1. l'indice scelto separa veri e falsi (media veri > media falsi)
  2. i falsi fermati devono essere > 0: se FactCG non ferma nulla, la soglia 0,5
     e' fuori scala e i numeri non valgono.
"""
import io
import json
import os
import sys
import time

os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS", "1")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

import torch  # noqa: E402
from transformers import AutoModelForSequenceClassification, AutoTokenizer  # noqa: E402

M = "yaxili96/FactCG-DeBERTa-v3-Large"
DATI = "benchmark/data/external/truthfulqa_pairs_heldout.jsonl"
OUT = "_ws4_factcg_heldout.jsonl"
SOGLIA = 0.5

print(f"  carico {M} su CPU…")
tok = AutoTokenizer.from_pretrained(M)
mod = AutoModelForSequenceClassification.from_pretrained(M)
mod.eval()

righe = [json.loads(x) for x in io.open(DATI, encoding="utf-8") if x.strip()]
print(f"  righe: {len(righe)}  soglia {SOGLIA}")

t0 = time.time()
out = io.open(OUT, "w", encoding="utf-8")
for i, r in enumerate(righe, 1):
    with torch.no_grad():
        x = tok(r.get("source") or "", r.get("claim") or "",
                return_tensors="pt", truncation=True, max_length=512)
        p = torch.softmax(mod(**x).logits[0], dim=-1).tolist()
    r["p"] = p
    out.write(json.dumps({"i": i, "label": r["label"], "p": p,
                          "category": r.get("category")}) + chr(10))
    if i % 150 == 0:
        print(f"    ...{i}/{len(righe)}  ({time.time() - t0:.0f}s)")
out.close()
print(f"  inferenza in {time.time() - t0:.0f}s -> {OUT}")

veri = [r for r in righe if r["label"] == 1]
falsi = [r for r in righe if r["label"] == 0]


def media(lst, idx):
    return sum(r["p"][idx] for r in lst) / len(lst) if lst else 0.0


print("\n  CONTROLLO 1 — quale indice separa veri e falsi:")
scelto, best = None, 0.0
for idx in (0, 1):
    mv, mf = media(veri, idx), media(falsi, idx)
    print(f"    indice {idx}: media sui veri {mv:.3f} · sui falsi {mf:.3f}"
          f"  (divario {mv - mf:+.3f})")
    if mv - mf > best:
        scelto, best = idx, mv - mf
if scelto is None:
    print("  CONTROLLO SPENTO: nessun indice separa => modello non utilizzabile")
    sys.exit(1)
print(f"    => SUPPORTED = indice {scelto} (divario {best:+.3f})")

vp = sum(1 for r in veri if r["p"][scelto] < SOGLIA)
ff = sum(1 for r in falsi if r["p"][scelto] < SOGLIA)
print(f"\n  == T1.1, FactCG a soglia {SOGLIA} ==")
print(f"    veri persi    {vp}/{len(veri)}  ({100*vp/len(veri):.1f}%)"
      f"     [moat: 88/300 = 29,3%]")
print(f"    falsi fermati {ff}/{len(falsi)}  ({100*ff/len(falsi):.1f}%)"
      f"     [moat: 260/300 = 86,7%]")
if ff == 0:
    print("  CONTROLLO 2 SPENTO: zero falsi fermati => soglia fuori scala")
    sys.exit(1)
pv = 100 * vp / len(veri)
print("\n  PREDIZIONE MIA (veri persi >=25%, falsi fermati >=80%):"
      f"  {'REGGE' if pv >= 25 and 100*ff/len(falsi) >= 80 else 'NON REGGE'}")
print(f"  FALSIFICATA se veri persi <20%:  {'SI' if pv < 20 else 'NO'}")
print(f"  PREDIZIONE DELLA RICERCA (<20% a falsita' <=18%):"
      f"  {'CONFERMATA' if pv < 20 else 'FALSIFICATA'}")
sys.exit(0)
