# -*- coding: utf-8 -*-
"""FINE-TUNE v3 — costruzione del DATASET, senza addestrare (mandato @lead-audit 20:44).

⛔ NON ADDESTRA. Scrive i file e conta. L'addestramento e' fermo: Aurelio usa il PC.

🔴 IL MANDATO SI CONTRADDICE, E LO RISOLVO COSI'. Chiede di mettere in train «i 61
veri sotto 5» e «i 40 falsi ammessi» e insieme che «TruthfulQA-600 resta test
esterno intoccabile». Ma quei 61 e quei 40 SONO righe di TruthfulQA-600:
metterli in addestramento e' addestrare sul test, e ogni numero misurato dopo su
quel banco sarebbe gonfio. Stessa cosa per «i 400 HaluEval», che sono
`halueval_qa_heldout` (200 righe x 2 claim) — il banco su cui @ws7 ha misurato il
55,0% e su cui sto misurando FactCG adesso.
⇒ Il train si costruisce dagli split DEV, che nessun banco di misura usa:
   `truthfulqa_pairs_dev.jsonl` (200) e `halueval_qa_dev.jsonl` (100 -> 200 claim).
   I banchi di misura restano intatti. La classe difficile («veri sotto 5»,
   «falsi ammessi») si RI-MISURA sul dev con lo stesso gate: e' un'esecuzione a
   parte, e finche' non c'e' resta un buco DICHIARATO, non riempito con quelli
   del test.

⚠️ E IL DEV NON E' DEL TUTTO PULITO — il punto di contatto e' PROPRIO la classe da
curare. Sei claim stanno in entrambi gli split di TruthfulQA e cinque su sei sono
ASTENSIONI («I have no comment», 2 nel dev e 18 nell'heldout; «Unknown»; «There
was no first human»; «There's no such language»; «Yes»). Addestrare su quelle
stringhe e poi misurare sull'heldout non distingue la generalizzazione dalla
memorizzazione della stringa. Vengono TOLTE dal train, e il controllo positivo
qui sotto deve vedere il numero scendere a zero.

I CASI dei banchi non li riscrivo: li ESTRAGGO dai file versionati con `ast`,
senza eseguirli (i banchi hanno effetti al momento dell'import).
"""
import ast
import io
import json
import os
import random
from collections import Counter

REPO = "C:/Users/aurel/Code/HippoAgent"
EXT = REPO + "/benchmark/data/external/"
BANCHI = REPO + "/docs/stato-reale/banchi/"
OUT = ("C:/Users/aurel/AppData/Local/Temp/claude/"
       "C--Users-aurel-Desktop-ProgettiAI/"
       "78ba9444-dd97-498f-bd48-07ca991638a4/scratchpad/")
SEED = 7          # lo stesso di benchmark/local_gate_finetune.py
QUOTA_VAL = 0.10  # la stessa: VAL stratificata che l'ottimizzatore non vede


def carica(percorso):
    return [json.loads(x) for x in io.open(percorso, encoding="utf-8") if x.strip()]


def costante(percorso, nome):
    """Legge una costante da un banco SENZA eseguirlo."""
    albero = ast.parse(io.open(percorso, encoding="utf-8").read())
    for nodo in albero.body:
        if isinstance(nodo, ast.Assign):
            for b in nodo.targets:
                if isinstance(b, ast.Name) and b.id == nome:
                    return ast.literal_eval(nodo.value)
    return None


righe = []   # ogni voce: source, claim, label, fonte, classe

# ── ① TruthfulQA dev ─────────────────────────────────────────────────────
td = carica(EXT + "truthfulqa_pairs_dev.jsonl")
th = carica(EXT + "truthfulqa_pairs_heldout.jsonl")
claim_di_test = {r["claim"] for r in th}
sporche = [r for r in td if r["claim"] in claim_di_test]
print(f"① truthfulqa-dev: {len(td)} claim")
print(f"   CONTAMINAZIONE col test: {len(sporche)} righe su {len(td)}"
      f" = {100*len(sporche)/len(td):.1f}%")
for c, n in Counter(r["claim"] for r in sporche).most_common():
    print(f"     {n}x  {c[:60]!r}")
for r in td:
    if r["claim"] in claim_di_test:
        continue
    righe.append({"source": r["source"], "claim": r["claim"], "label": r["label"],
                  "fonte": "truthfulqa-dev", "classe": r.get("category") or "?"})
print(f"   -> tenute {sum(1 for x in righe if x['fonte'] == 'truthfulqa-dev')}")

# ── ② HaluEval dev: 100 righe -> 200 claim, come il banco di @ws3 ────────
hd = carica(EXT + "halueval_qa_dev.jsonl")
for r in hd:
    src = r["knowledge"]
    q = r["question"]
    righe.append({"source": src, "claim": f"{q} {r['right_answer']}", "label": 1,
                  "fonte": "halueval-dev", "classe": "qa"})
    righe.append({"source": src, "claim": f"{q} {r['hallucinated_answer']}", "label": 0,
                  "fonte": "halueval-dev", "classe": "qa"})
print(f"② halueval-dev: {len(hd)} righe -> "
      f"{sum(1 for x in righe if x['fonte'] == 'halueval-dev')} claim")

# ── ③ le coppie numeriche di @ws3: (classe, fonte, modello, identico, trasformato, falso)
B3 = BANCHI + "ws3-M5-T51-le-tre-classi-numeriche-non-misurate.py"
casi3 = costante(B3, "CASI") or []
for classe, src, modello, ident, trasf, falso in casi3:
    righe.append({"source": src, "claim": modello.format(n=ident), "label": 1,
                  "fonte": "ws3-numerico", "classe": classe + "/identica"})
    righe.append({"source": src, "claim": modello.format(n=trasf), "label": 1,
                  "fonte": "ws3-numerico", "classe": classe + "/trasformata"})
    righe.append({"source": src, "claim": modello.format(n=falso), "label": 0,
                  "fonte": "ws3-numerico", "classe": classe + "/falso"})
print(f"③ ws3-numerico: {len(casi3)} casi -> "
      f"{sum(1 for x in righe if x['fonte'] == 'ws3-numerico')} claim")

# ── ④ la batteria italiana di @ws3: (classe, src_it, vero_it, falso_it, src_en, vero_en, falso_en)
B4 = BANCHI + "ws3-la-batteria-italiana-caso-o-classe.py"
casi4 = costante(B4, "CASI") or []
for classe, s_it, v_it, f_it, s_en, v_en, f_en in casi4:
    righe.append({"source": s_it, "claim": v_it, "label": 1,
                  "fonte": "ws3-italiano", "classe": classe + "/IT"})
    righe.append({"source": s_it, "claim": f_it, "label": 0,
                  "fonte": "ws3-italiano", "classe": classe + "/IT"})
    righe.append({"source": s_en, "claim": v_en, "label": 1,
                  "fonte": "ws3-italiano", "classe": classe + "/EN"})
    righe.append({"source": s_en, "claim": f_en, "label": 0,
                  "fonte": "ws3-italiano", "classe": classe + "/EN"})
print(f"④ ws3-italiano: {len(casi4)} casi -> "
      f"{sum(1 for x in righe if x['fonte'] == 'ws3-italiano')} claim")

# ── I CONTROLLI CHE DEVONO ACCENDERSI ───────────────────────────────────
print("\n══ CONTROLLI ══")
resta = sum(1 for r in righe if r["claim"] in claim_di_test)
print(f"  ① claim del train presenti in TruthfulQA-600: {len(sporche)} PRIMA"
      f" -> {resta} ADESSO   {'ACCESO' if len(sporche) > 0 and resta == 0 else 'SPENTO'}")
hh = carica(EXT + "halueval_qa_heldout.jsonl")
dom_test = {r["question"] for r in hh}
tocca = sum(1 for r in righe if r["fonte"] == "halueval-dev"
            and r["claim"].split("?")[0] + "?" in dom_test)
print(f"  ② domande del train presenti in HaluEval-400: {tocca}"
      f"   {'ACCESO' if tocca == 0 else 'SPENTO'}")
dupli = len(righe) - len({(r["source"], r["claim"]) for r in righe})
print(f"  ③ coppie (source, claim) duplicate dentro al train: {dupli}"
      f"   {'ACCESO' if dupli == 0 else 'da guardare'}")

# ── SPLIT train/val stratificato per (fonte, label), seed della ricetta ──
rng = random.Random(SEED)
strati = {}
for r in righe:
    strati.setdefault((r["fonte"], r["label"]), []).append(r)
train, val = [], []
for chiave, gruppo in sorted(strati.items()):
    rng.shuffle(gruppo)
    n_val = max(1, int(round(len(gruppo) * QUOTA_VAL)))
    val += gruppo[:n_val]
    train += gruppo[n_val:]

print("\n══ COMPOSIZIONE ══")
print(f"  {'fonte':<18} {'veri':>6} {'falsi':>6} {'tot':>6}   {'train':>6} {'val':>5}")
for f in sorted({r["fonte"] for r in righe}):
    v = sum(1 for r in righe if r["fonte"] == f and r["label"] == 1)
    fa = sum(1 for r in righe if r["fonte"] == f and r["label"] == 0)
    tr = sum(1 for r in train if r["fonte"] == f)
    va = sum(1 for r in val if r["fonte"] == f)
    print(f"  {f:<18} {v:>6} {fa:>6} {v+fa:>6}   {tr:>6} {va:>5}")
v = sum(1 for r in righe if r["label"] == 1)
print(f"  {'TOTALE':<18} {v:>6} {len(righe)-v:>6} {len(righe):>6}"
      f"   {len(train):>6} {len(val):>5}")

print("\n  per CLASSE (le 12 piu' numerose):")
for c, n in Counter(r["classe"] for r in righe).most_common(12):
    print(f"    {n:>4}  {c}")

for nome, dati in (("v3_train.jsonl", train), ("v3_val.jsonl", val)):
    with io.open(OUT + nome, "w", encoding="utf-8") as fh:
        for r in dati:
            fh.write(json.dumps(r, ensure_ascii=False) + chr(10))
    print(f"\n  scritto {OUT}{nome}  ({len(dati)} righe,"
          f" {os.path.getsize(OUT + nome)} byte)")

# ── LA STIMA DI TEMPO, con dentro cio' che e' CALCOLATO e cio' che e' STIMATO
B = 8       # --batch della ricetta
E = 2       # --epochs
step = ((len(train) + B - 1) // B) * E
print("\n══ QUANTO CI VUOLE (ricetta benchmark/local_gate_finetune.py) ══")
print(f"  CALCOLATO: {len(train)} esempi / batch {B} x {E} epoche = {step} passi"
      f" di ottimizzazione (max_length 512, AdamW lr 2e-5, OneCycleLR)")
print("  STIMATO (non misurato: non ho una GPU sotto mano e non addestro ora):")
print("    · deberta-v3-base = 184M parametri; a 512 token e batch 8 una GPU")
print("      consumer fa ~2-4 passi/s in training")
print(f"    ⇒ {step} passi ≈ {step/4:.0f}-{step/2:.0f} s di GPU, piu' il carico del modello")
print("  🔑 IL TEMPO NON E' IL VINCOLO, E VA DETTO: con questo dataset")
print("     l'addestramento dura un minuto. Il vincolo e' QUANTI ESEMPI ci sono.")
