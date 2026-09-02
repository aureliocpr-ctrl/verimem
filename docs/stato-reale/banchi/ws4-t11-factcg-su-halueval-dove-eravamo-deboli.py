"""T1.1 SECONDO BRACCIO — FactCG sui 400 di HaluEval, dove il nostro gate e' DEBOLE.

Su TruthfulQA il verdetto e' chiuso e sfavorevole a FactCG: a pari veri persi
(88/300) ferma 199/300 = 66,3% contro 260/300 = 86,7% del nostro moat, AUROC
0,743. Ma TruthfulQA e' Q/A: la «source» e' la DOMANDA, non un documento.
HaluEval QA ha una `knowledge` che e' una vera fonte documentale — cioe' il
compito NATIVO di FactCG — ed e' proprio li' che il nostro gate ferma solo il
55,0% dei falsi. E' l'unico posto dove FactCG puo' vincere.

PREDIZIONE DEPOSITATA PRIMA (canale 89e87c7a, 02/09 20:23, e riaffermata qui):
  · a PARI veri persi del nostro gate su HaluEval (19,0%), FactCG ferma
    PIU' del 55,0% dei falsi — la predizione e' «>60%».
  · AUROC > 0,80  (contro 0,743 su TruthfulQA)
  · IL PERCHE', che e' la parte falsificabile: se il divario dipende dal
    COMPITO (fonte documentale contro domanda) e non dal modello, FactCG deve
    salire QUI e restare giu' LA'. Se sale in tutti e due o scende in tutti e
    due, la spiegazione «e' il compito» e' sbagliata.
  · FALSIFICATA se: falsi fermati a iso-recall <= 55,0% (non batte il nostro
    dove siamo deboli) OPPURE AUROC <= 0,75 (non meglio che su TruthfulQA).

I DATI sono quelli di @ws3 (`halueval_come_truthfulqa.jsonl`, 400 claim: 200
veri + 200 falsi), gli stessi che ha usato @ws7 per il 55,0%: non li rifaccio
apposta, perche' un adattamento mio renderebbe i numeri NON confrontabili con i
suoi. NOTA: il suo banco lo chiama «halueval-399» — `wc -l` ne conta 399 perche'
l'ultima riga non finisce con a capo, ma i claim sono 400 (200 + 200).

CONTROLLI CHE DEVONO ACCENDERSI:
  1. l'indice 1 = SUPPORTED deve separare veri e falsi anche QUI (media sui veri
     maggiore che sui falsi). Se non separa, il modello non e' utilizzabile su
     questo corpus e il banco si ferma: la mappatura era stata determinata su
     TruthfulQA, non su HaluEval, e non si eredita senza controllo.
  2. i falsi fermati alla soglia iso-recall devono essere > 0.
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
# il dump adattato di @ws3: sta nel SUO scratchpad e non e' nel repo.
# Si passa con WS3_HALUEVAL=<path>, come fa il banco di @ws3 stesso.
DATI = os.environ.get("WS3_HALUEVAL", "")
if not DATI or not os.path.exists(DATI):
    raise SystemExit(
        "  QUESTO BANCO NON PUO' GIRARE: manca il dump HaluEval adattato\n"
        "  di @ws3 (400 claim). Passalo con WS3_HALUEVAL=<path>, oppure\n"
        "  chiedi a @ws3 di versarlo: non lo verso io, e' suo.")
OUT = ("docs/stato-reale/banchi/factcg_halueval.jsonl")
IDX = 1          # SUPPORTED, determinato su TruthfulQA — RIVERIFICATO sotto
VERI_PERSI_NOSTRI = 0.190   # il nostro gate su HaluEval (ws7)
FALSI_FERMATI_NOSTRI = 55.0

righe = [json.loads(x) for x in io.open(DATI, encoding="utf-8") if x.strip()]
veri = [r for r in righe if r["label"] == 1]
falsi = [r for r in righe if r["label"] == 0]
print(f"  righe {len(righe)}  (veri {len(veri)} · falsi {len(falsi)})")

print(f"  carico {M} su CPU…")
tok = AutoTokenizer.from_pretrained(M)
mod = AutoModelForSequenceClassification.from_pretrained(M)
mod.eval()

t0 = time.time()
out = io.open(OUT, "w", encoding="utf-8")
for i, r in enumerate(righe, 1):
    with torch.no_grad():
        x = tok(r.get("source") or "", r.get("claim") or "",
                return_tensors="pt", truncation=True, max_length=512)
        p = torch.softmax(mod(**x).logits[0], dim=-1).tolist()
    r["p"] = p[IDX]
    out.write(json.dumps({"i": i, "label": r["label"], "p": p}) + chr(10))
    if i % 100 == 0:
        print(f"    ...{i}/{len(righe)}  ({time.time() - t0:.0f}s)", flush=True)
out.close()
print(f"  inferenza in {time.time() - t0:.0f}s -> {OUT}")


def media(lst):
    return sum(r["p"] for r in lst) / len(lst) if lst else 0.0


mv, mf = media(veri), media(falsi)
print(f"\n  CONTROLLO 1 — l'indice {IDX} separa anche su HaluEval?")
print(f"    media sui veri {mv:.3f} · sui falsi {mf:.3f}  (divario {mv - mf:+.3f})")
if mv <= mf:
    print("    CONTROLLO SPENTO: non separa => la mappatura di TruthfulQA non vale qui")
    sys.exit(1)
print("    acceso.")

# ── AUROC, che non dipende da nessuna soglia ─────────────────────────────
coppie = (sum(1 for v in veri for f in falsi if v["p"] > f["p"])
          + 0.5 * sum(1 for v in veri for f in falsi if v["p"] == f["p"]))
auroc = coppie / (len(veri) * len(falsi))
print(f"\n  AUROC FactCG su HaluEval: {auroc:.3f}   [su TruthfulQA era 0,743]")

# ── LA CURVA ─────────────────────────────────────────────────────────────
print(f"\n  {'soglia':>7}  {'veri persi':>14}  {'falsi fermati':>14}")
for s10 in range(5, 96, 5):
    s = s10 / 100.0
    vp = sum(1 for r in veri if r["p"] < s)
    ff = sum(1 for r in falsi if r["p"] < s)
    print(f"  {s:>7.2f}  {vp:>4}/{len(veri)} {100*vp/len(veri):>5.1f}%"
          f"  {ff:>4}/{len(falsi)} {100*ff/len(falsi):>5.1f}%")

# ── IL NUMERO CHE DECIDE ─────────────────────────────────────────────────
bersaglio = int(round(VERI_PERSI_NOSTRI * len(veri)))
ordinati = sorted(veri, key=lambda r: r["p"])
soglia_iso = ordinati[bersaglio - 1]["p"] + 1e-9
ff_iso = sum(1 for r in falsi if r["p"] < soglia_iso)
vp_iso = sum(1 for r in veri if r["p"] < soglia_iso)
pf = 100 * ff_iso / len(falsi)
print("\n  == ISO-RECALL: a PARI veri persi del nostro gate su HaluEval ==")
print(f"    bersaglio {bersaglio}/{len(veri)} veri persi ({100*VERI_PERSI_NOSTRI:.1f}%)"
      f" · raggiunti {vp_iso} · soglia {soglia_iso:.4f}")
print(f"    FactCG ferma      {ff_iso}/{len(falsi)} = {pf:.1f}% dei falsi")
print(f"    il nostro gate    {FALSI_FERMATI_NOSTRI:.1f}%")
print(f"    => differenza {pf - FALSI_FERMATI_NOSTRI:+.1f} punti")
if ff_iso == 0:
    print("  CONTROLLO 2 SPENTO: zero falsi fermati")
    sys.exit(1)

print("\n  == I VERDETTI, col VINCOLO nel codice ==")
batte = pf > FALSI_FERMATI_NOSTRI
print(f"    PREDIZIONE MIA «>60%»:            "
      f"{'REGGE' if pf > 60 else 'FALSIFICATA'}  ({pf:.1f}%)")
print(f"    PREDIZIONE MIA «AUROC >0,80»:     "
      f"{'REGGE' if auroc > 0.80 else 'FALSIFICATA'}  ({auroc:.3f})")
print(f"    batte il nostro gate QUI:         {'SI' if batte else 'NO'}")
sale_qui_e_no_la = auroc > 0.743 and pf > FALSI_FERMATI_NOSTRI
print(f"    LA SPIEGAZIONE «e' il COMPITO» (sale qui, sotto la' su TruthfulQA):"
      f"  {'REGGE' if sale_qui_e_no_la else 'FALSIFICATA'}")
sys.exit(0)
