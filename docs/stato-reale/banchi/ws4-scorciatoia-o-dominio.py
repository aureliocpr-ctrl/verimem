# -*- coding: utf-8 -*-
"""IL CONTROLLO CHE SEPARA DUE SPIEGAZIONI del 9% sulle astensioni false nuove.

Puo' essere (a) la SCORCIATOIA «forma di astensione ⇒ vero», oppure (b) un
effetto di DOMINIO: le nuove vengono da `squad_v2_dev`, quelle viste in training
da `halueval_qa_dev`. Le misuro anche sulle VISTE:
  * se sulle viste ferma MOLTO di piu' ⇒ memorizzazione + dominio;
  * se ferma poco anche li' ⇒ il modello ha imparato che quella FORMA e' vera, e
    non e' una questione di corpus.
"""
import io
import json
import os

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

# la cartella dei dati: relativa al repo per default (e' dove il banco
# `ws4-le-astensioni-erano-gia-nel-repo.py` scrive), sovrascrivibile.
SC = os.environ.get("WS4_OUT", "docs/stato-reale/banchi/_out/")
MOD = SC + "ce_v31"
SOGLIA = 0.6168          # quella a pari veri persi del gate attuale

tok = AutoTokenizer.from_pretrained(MOD)
mod = AutoModelForSequenceClassification.from_pretrained(MOD)
mod.eval()

righe = [json.loads(x) for x in io.open(SC + "v31_astensioni.jsonl",
                                        encoding="utf-8") if x.strip()]
false_viste = [r for r in righe if r["classe"] == "astensione-FALSA"]
vere_viste = [r for r in righe if r["classe"] == "astensione"]


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


pf = punteggi(false_viste)
pv = punteggi(vere_viste)
ff = sum(1 for p in pf if p < SOGLIA)
av = sum(1 for p in pv if p >= SOGLIA)
print(f"  astensioni FALSE **viste** nel train:  ferma {ff}/{len(pf)}"
      f" = {100*ff/len(pf):.1f}%")
print("  astensioni FALSE **mai viste** (squad):  ferma 9/100 = 9,0%"
      "   (misurato prima)")
print(f"  astensioni VERE viste nel train:       ammette {av}/{len(pv)}"
      f" = {100*av/len(pv):.1f}%")
print()
if 100 * ff / len(pf) < 50:
    print("  ⇒ ferma poco ANCHE sulle viste: non e' memorizzazione ne' dominio.")
    print("    Il modello ha imparato che quella FORMA e' vera, punto.")
else:
    print("  ⇒ sulle viste ferma molto di piu': memorizzazione e/o effetto di")
    print("    dominio, e il 9% sulle nuove va riletto con quella cautela.")
