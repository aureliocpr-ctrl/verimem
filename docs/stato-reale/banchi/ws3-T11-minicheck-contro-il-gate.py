# -*- coding: utf-8 -*-
"""T1.1 braccio 2 — MiniCheck contro il gate attuale, sugli stessi due dump.

    python docs/stato-reale/banchi/ws3-T11-minicheck-contro-il-gate.py --limite 20
    python docs/stato-reale/banchi/ws3-T11-minicheck-contro-il-gate.py

DUE POPOLAZIONI, sempre: `veri persi` (label=1 giudicati non supportati) e
`falsi fermati` (label=0 giudicati non supportati). Un verificatore misurato
sui soli falsi sembra sempre ottimo: basta rifiutare tutto.

RIFERIMENTO da battere — il GATE ATTUALE sullo stesso banco, misurato da
un'altra istanza: **veri persi 19,0%**, **falsi fermati 55,0%**.

🔮 PREDIZIONE depositata sul canale PRIMA di eseguire (02/09 19:57):
  ① MiniCheck ferma piu' falsi del gate: **>=65%**
  ② e perde piu' veri: **>=25%**
  ③ ⇒ non un rimpiazzo, uno SCAMBIO. Se batte il gate su ENTRAMBE le colonne
     (>=65% falsi fermati E <=19% veri persi) la predizione e' FALSIFICATA.

⏱️ CRITERIO DI STOP, misurato e non stimato: con `--limite` si misura il tempo
su un campione e si estrapola. Oltre i 30 minuti stimati per i 999, si consegna
il TEMPO invece del risultato.

⚠️ Il modello e' `lytang/MiniCheck-DeBERTa-v3-Large`, NON i DeBERTa-NLI generici
gia' in cache (MNLI/FEVER/ANLI): sono addestrati per un altro compito e
chiamarli MiniCheck falserebbe il nome sul numero.
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

MODELLO = "lytang/MiniCheck-DeBERTa-v3-Large"
SOGLIA = 0.5

RADICE = Path(__file__).resolve().parents[3]
DUMP = [
    ("truthfulqa-600",
     RADICE / "benchmark/data/external/truthfulqa_pairs_heldout.jsonl"),
    ("halueval-399",
     Path(os.environ.get("WS3_HALUEVAL", "")) if os.environ.get("WS3_HALUEVAL")
     else Path("C:/Users/aurel/AppData/Local/Temp/claude/"
               "C--Users-aurel-Desktop-ProgettiAI/"
               "c062024e-cc77-4fac-ba67-fb1db54449b6/scratchpad/"
               "halueval_come_truthfulqa.jsonl")),
]


def carica(percorso, limite):
    righe = []
    with open(percorso, encoding="utf-8") as fh:
        for riga in fh:
            riga = riga.strip()
            if not riga:
                continue
            try:
                d = json.loads(riga)
            except Exception:
                continue
            if "source" in d and "claim" in d and "label" in d:
                righe.append(d)
            if limite and len(righe) >= limite:
                break
    return righe


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limite", type=int, default=0,
                    help="quanti esempi per dump (0 = tutti)")
    args = ap.parse_args()

    import torch
    from transformers import (AutoModelForSequenceClassification,
                              AutoTokenizer)

    print(f"modello: {MODELLO}   soglia: {SOGLIA}   CPU")
    t0 = time.time()
    tok = AutoTokenizer.from_pretrained(MODELLO)
    mod = AutoModelForSequenceClassification.from_pretrained(MODELLO)
    mod.eval()
    t_load = time.time() - t0
    print(f"caricamento: {t_load:.1f}s\n")

    complessivo = {}
    for nome, percorso in DUMP:
        if not percorso.exists():
            print(f"⚠️  {nome}: file assente ({percorso}) — salto")
            continue
        dati = carica(percorso, args.limite)
        veri = [d for d in dati if int(d["label"]) == 1]
        falsi = [d for d in dati if int(d["label"]) == 0]
        veri_persi = falsi_fermati = 0
        t1 = time.time()
        for d in dati:
            enc = tok(d["source"], d["claim"], truncation=True,
                      max_length=512, return_tensors="pt")
            with torch.no_grad():
                logits = mod(**enc).logits
            # due teste = (non supportato, supportato); una sola = logit di
            # supporto. Si legge la forma invece di assumerla.
            if logits.shape[-1] == 2:
                p_supporto = float(torch.softmax(logits, dim=-1)[0, 1])
            else:
                p_supporto = float(torch.sigmoid(logits)[0, 0])
            supportato = p_supporto >= SOGLIA
            if int(d["label"]) == 1 and not supportato:
                veri_persi += 1
            if int(d["label"]) == 0 and not supportato:
                falsi_fermati += 1
        dt = time.time() - t1
        complessivo[nome] = (veri_persi, len(veri), falsi_fermati, len(falsi), dt)
        print(f"{nome}: {len(dati)} esempi in {dt:.1f}s "
              f"({dt / max(1, len(dati)):.2f}s/esempio)")
        if veri:
            print(f"   VERI PERSI    {veri_persi}/{len(veri)} "
                  f"= {100 * veri_persi / len(veri):.1f}%")
        if falsi:
            print(f"   FALSI FERMATI {falsi_fermati}/{len(falsi)} "
                  f"= {100 * falsi_fermati / len(falsi):.1f}%")
        print()

    if args.limite:
        per_esempio = sum(v[4] for v in complessivo.values()) / max(
            1, sum(1 for _ in complessivo) * args.limite)
        stima = per_esempio * 999 / 60
        print(f"⏱️  stima per i 999: {stima:.1f} minuti "
              f"({per_esempio:.2f}s/esempio)")
        print("   oltre 30 minuti -> si consegna il tempo, non il risultato")
    else:
        print("=" * 70)
        print("CONFRONTO col GATE ATTUALE (altra istanza, stesso banco):")
        print("   gate attuale   veri persi 19,0%   falsi fermati 55,0%")
        for nome, (vp, nv, ff, nf, _dt) in complessivo.items():
            print(f"   MiniCheck {nome:16s} veri persi "
                  f"{100 * vp / max(1, nv):.1f}%   falsi fermati "
                  f"{100 * ff / max(1, nf):.1f}%")
        print("\n  predizione: >=65% falsi fermati E >=25% veri persi")
        print("  se BATTE il gate su entrambe -> predizione FALSIFICATA")


if __name__ == "__main__":
    sys.exit(main())
