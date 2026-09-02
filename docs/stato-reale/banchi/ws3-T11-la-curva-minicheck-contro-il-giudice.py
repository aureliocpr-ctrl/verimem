# -*- coding: utf-8 -*-
"""T1.1 — LA CURVA: MiniCheck contro il nostro giudice, a parità di veri persi.

    python docs/stato-reale/banchi/ws3-T11-la-curva-minicheck-contro-il-giudice.py

PERCHE' UN PUNTO SOLO NON DECIDE. A soglia 0,5 MiniCheck fa 96,7/66,7 e il
nostro gate 86,7/29,3: sono **due punti di due curve diverse**, e confrontarli
direttamente non dice quale sistema sia migliore — dice solo che sono tarati
diversamente. La domanda che decide e' una sola:

    **a PARI veri persi del nostro gate, quanti falsi ferma MiniCheck?**

    TruthfulQA   gate 29,3% veri persi -> 86,7% falsi fermati
    HaluEval     gate 19,0% veri persi -> 55,0% falsi fermati

🔮 PREDIZIONE depositata sul canale PRIMA di eseguire (02/09 20:21):
  ① a pari veri persi MiniCheck ferma **MENO** di 86,7% su TruthfulQA (vince il
     gate) e **PIU'** di 55,0% su HaluEval (vince MiniCheck)
     ⇒ **nessun verdetto unico: dipende dal banco**. Se il verdetto e' uguale
     sui due dump, la predizione e' FALSIFICATA.
  ② i due AUROC stanno **entro 0,05** l'uno dall'altro.
  ③ la curva di MiniCheck e' ripida fra 0,05 e 0,3.

⚠️ ENTRAMBI I SISTEMI SONO MISURATI OGGI, sugli STESSI casi, nella STESSA
esecuzione. Esiste un file di luglio con gli score del giudice su questi 600
(`benchmark/results/external_grounding_truthfulqa_heldout_2026-07-17.json`,
AUROC 0,829) e NON lo uso come braccio: ha un mese e mezzo, e confrontare un
sistema di oggi con uno di luglio e' il difetto che abbiamo passato la notte a
misurare. Resta come riferimento storico, per dire se il giudice si e' mosso.

⚠️ Le due scale sono diverse per costruzione — MiniCheck da' una probabilita'
in [0,1], il nostro giudice un punteggio in [0,100]. Per questo il confronto
NON si fa a soglia uguale ma **a pari veri persi**, e l'AUROC (che e' invariante
per riscalatura monotona) e' l'unico numero direttamente confrontabile.
"""
import json
import sys
import time
from pathlib import Path

MODELLO = "lytang/MiniCheck-DeBERTa-v3-Large"
RADICE = Path(__file__).resolve().parents[3]
USCITA = Path(__file__).resolve().parent / "_ws3_curva_scores.json"

DUMP = [
    ("truthfulqa-600",
     RADICE / "benchmark/data/external/truthfulqa_pairs_heldout.jsonl",
     0.293, 0.867),          # (veri persi, falsi fermati) del NOSTRO gate
    ("halueval-400",
     Path("C:/Users/aurel/AppData/Local/Temp/claude/"
          "C--Users-aurel-Desktop-ProgettiAI/"
          "c062024e-cc77-4fac-ba67-fb1db54449b6/scratchpad/"
          "halueval_come_truthfulqa.jsonl"),
     0.190, 0.550),
]
SOGLIE_MINICHECK = [0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 0.9]


def carica(percorso):
    fuori = []
    for riga in percorso.read_text(encoding="utf-8").splitlines():
        riga = riga.strip()
        if not riga:
            continue
        try:
            d = json.loads(riga)
        except Exception:
            continue
        if "source" in d and "claim" in d and "label" in d:
            fuori.append(d)
    return fuori


def auroc(pos, neg):
    """Probabilita' che un positivo prenda uno score piu' alto di un negativo.

    Invariante per riscalatura monotona: e' il motivo per cui e' l'unico numero
    confrontabile fra due sistemi con scale diverse.
    """
    if not pos or not neg:
        return None
    vinte = sum((p > n) + 0.5 * (p == n) for p in pos for n in neg)
    return round(vinte / (len(pos) * len(neg)), 4)


def a_pari_veri_persi(pos, neg, quota_persi):
    """Quanti falsi ferma il sistema quando perde ESATTAMENTE `quota_persi`.

    La soglia si prende dal quantile dei POSITIVI: se accetto di perdere il
    29,3% dei veri, taglio sotto il loro 29,3-esimo percentile. Poi si conta
    quanti negativi cadono sotto quella stessa soglia.
    """
    if not pos or not neg:
        return None, None
    ordinati = sorted(pos)
    idx = min(len(ordinati) - 1, max(0, int(round(quota_persi * len(ordinati)))))
    soglia = ordinati[idx]
    fermati = sum(1 for n in neg if n < soglia)
    persi = sum(1 for p in pos if p < soglia)
    return soglia, (fermati / len(neg), persi / len(pos))


def main():
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    from verimem.local_grounding import LocalGroundingJudge

    print(f"MiniCheck: {MODELLO}\nGiudice:   LocalGroundingJudge (oggi)\n")
    tok = AutoTokenizer.from_pretrained(MODELLO)
    mod = AutoModelForSequenceClassification.from_pretrained(MODELLO)
    mod.eval()
    giudice = LocalGroundingJudge()

    tutto = {}
    for nome, percorso, gate_persi, gate_fermati in DUMP:
        if not percorso.exists():
            print(f"⚠️  {nome}: file assente — salto")
            continue
        dati = carica(percorso)
        mc = {"pos": [], "neg": []}
        gd = {"pos": [], "neg": []}
        t0 = time.time()
        for d in dati:
            enc = tok(d["source"], d["claim"], truncation=True,
                      max_length=512, return_tensors="pt")
            with torch.no_grad():
                logits = mod(**enc).logits
            p = (float(torch.softmax(logits, dim=-1)[0, 1])
                 if logits.shape[-1] == 2
                 else float(torch.sigmoid(logits)[0, 0]))
            g = float(giudice.score(d["source"], d["claim"]))
            dove = "pos" if int(d["label"]) == 1 else "neg"
            mc[dove].append(p)
            gd[dove].append(g)
        dt = time.time() - t0
        tutto[nome] = {"minicheck": mc, "giudice": gd,
                       "gate": [gate_persi, gate_fermati],
                       "n": len(dati), "secondi": round(dt, 1)}
        print(f"{nome}: {len(dati)} casi in {dt:.0f}s "
              f"(pos {len(mc['pos'])}, neg {len(mc['neg'])})")

    USCITA.write_text(json.dumps(tutto), encoding="utf-8")
    print(f"\nscore salvati in {USCITA.name}\n")

    for nome, d in tutto.items():
        mc, gd = d["minicheck"], d["giudice"]
        gate_persi, gate_fermati = d["gate"]
        print("=" * 78)
        print(f"{nome}   (n={d['n']})\n")
        print("  MiniCheck — la curva")
        print("  %-10s %14s %16s" % ("soglia", "VERI persi", "FALSI fermati"))
        for s in SOGLIE_MINICHECK:
            vp = sum(1 for p in mc["pos"] if p < s) / max(1, len(mc["pos"]))
            ff = sum(1 for n in mc["neg"] if n < s) / max(1, len(mc["neg"]))
            print("  %-10.2f %13.1f%% %15.1f%%" % (s, 100 * vp, 100 * ff))

        print(f"\n  AUROC   MiniCheck {auroc(mc['pos'], mc['neg'])}"
              f"   ·   giudice {auroc(gd['pos'], gd['neg'])}")
        print("  (riferimento storico del giudice sui 600 di TruthfulQA, "
              "17/07: 0.829)")

        print(f"\n  🎯 IL NUMERO CHE DECIDE — a pari veri persi del gate "
              f"({100 * gate_persi:.1f}%):")
        _s, mc_res = a_pari_veri_persi(mc["pos"], mc["neg"], gate_persi)
        _s2, gd_res = a_pari_veri_persi(gd["pos"], gd["neg"], gate_persi)
        if mc_res:
            print(f"     MiniCheck ferma {100 * mc_res[0]:.1f}% dei falsi "
                  f"(perdendone {100 * mc_res[1]:.1f}% di veri)")
        if gd_res:
            print(f"     il giudice OGGI {100 * gd_res[0]:.1f}% "
                  f"(perdendone {100 * gd_res[1]:.1f}%)")
        print(f"     il GATE dichiarato  {100 * gate_fermati:.1f}%")
        if mc_res:
            verdetto = ("MiniCheck VINCE" if mc_res[0] > gate_fermati
                        else "il GATE VINCE")
            print(f"     ⇒ {verdetto}")
    print("\n  predizione: TruthfulQA -> vince il gate · HaluEval -> vince "
          "MiniCheck (verdetto DIVERSO sui due dump)")


if __name__ == "__main__":
    sys.exit(main())
