# -*- coding: utf-8 -*-
"""LA CONTRO-IPOTESI CHE AVEVO DICHIARATO APERTA, chiusa con i dati che ho.

In W7-134 ho scritto: «non ho provato se il difetto sparisce allungando
l'addestramento: potrebbe essere SOTTO-ADDESTRAMENTO invece che scorciatoia, e
quella e' la contro-ipotesi che non ho falsificato». Un limite dichiarato e' un
debito, e questo si paga in un minuto invece che con un secondo fine-tune.

LE TRE SPIEGAZIONI, e il numero che le separa — l'AUROC fra astensioni VERE e
FALSE calcolato sui casi VISTI in addestramento:
  (a) SOTTO-ADDESTRAMENTO      AUROC ~0,5 sul train: non ha ancora imparato a
                               distinguerle nemmeno dove le ha viste ⇒ piu'
                               epoche potrebbero bastare
  (b) CALIBRAZIONE             AUROC alto sul train ma la soglia cade nel punto
                               sbagliato ⇒ non serve riaddestrare, serve tarare
  (c) SCORCIATOIA              AUROC alto sul train e crollo sulle NUOVE ⇒ ha
                               imparato i casi, non la regola

⚠️ Non e' inferenza pesante: 300 forward pass, circa un minuto. Prendo lo slot
lo stesso perche' la regola non fa eccezioni per i lavori corti.
"""
import io
import json
import os

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

SC = os.environ.get("WS4_OUT", "docs/stato-reale/banchi/_out/")
tok = AutoTokenizer.from_pretrained(SC + "ce_v31")
mod = AutoModelForSequenceClassification.from_pretrained(SC + "ce_v31")
mod.eval()

righe = [json.loads(x) for x in io.open(SC + "v31_astensioni.jsonl",
                                        encoding="utf-8") if x.strip()]
vere = [r for r in righe if r["classe"] == "astensione"]
false_ = [r for r in righe if r["classe"] == "astensione-FALSA"]


def punteggi(rr):
    out = []
    with torch.no_grad():
        for i in range(0, len(rr), 16):
            lotto = rr[i:i + 16]
            enc = tok([b["source"] for b in lotto], [b["claim"] for b in lotto],
                      truncation="longest_first", max_length=512,
                      padding=True, return_tensors="pt")
            out += torch.sigmoid(mod(**enc).logits.squeeze(-1)).tolist()
    return out


pv, pf = punteggi(vere), punteggi(false_)
coppie = (sum(1 for a in pv for b in pf if a > b)
          + 0.5 * sum(1 for a in pv for b in pf if a == b))
auroc = coppie / (len(pv) * len(pf))

print(f"  astensioni VERE viste {len(pv)} · FALSE viste {len(pf)}")
print(f"  punteggio medio: vere {sum(pv)/len(pv):.3f} · false {sum(pf)/len(pf):.3f}")
print(f"\n  AUROC sul TRAIN fra astensioni vere e false: {auroc:.3f}")
print("\n  == QUALE DELLE TRE SPIEGAZIONI ==")
if auroc < 0.65:
    print("    (a) SOTTO-ADDESTRAMENTO: non le distingue nemmeno dove le ha")
    print("        viste ⇒ la mia conclusione «ha imparato la forma» va")
    print("        ammorbidita: forse non ha ancora imparato NIENTE di questa")
    print("        classe, e piu' epoche sono un esperimento sensato.")
elif auroc >= 0.85:
    print("    (c) SCORCIATOIA: sul train le separa bene e sulle nuove crolla")
    print("        (9/100) ⇒ ha imparato i CASI, non la regola. Piu' epoche")
    print("        peggiorerebbero, non migliorerebbero.")
else:
    print("    (b) VIA DI MEZZO: separa in parte. Serve guardare la soglia")
    print("        prima di riaddestrare — puo' essere calibrazione.")
print(f"\n  ⚠️ il confronto che chiude: sulle NUOVE ne ferma 9/100 = 9,0%.")
