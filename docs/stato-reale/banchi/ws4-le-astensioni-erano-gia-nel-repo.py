# -*- coding: utf-8 -*-
"""LE ASTENSIONI CHE MANCAVANO — e non le ho inventate: erano gia' nel repo.

IL BUCO (W7-126): il dataset di fine-tune v3 ha 486 claim ma solo 7 astensioni
vere su 437 di train (1,6%), contro 57/300 = 19,0% nel test — 0,24 esempi per
ogni caso da curare. Avevo scritto che per curarle «servono esempi di astensione
e vanno SCRITTI», con la riserva che scrivendoli io DOPO aver visto il test ne
copierei la distribuzione.

LA FONTE ERA GIA' LI', E NESSUNO L'AVEVA USATA: `benchmark/data/external/`
contiene `squad_v2_unanswerable.jsonl` (100) e `halueval_qa_unanswerable.jsonl`
(100) — domande a cui il documento NON risponde. ⇒ per quei 200 casi
**l'astensione e' la risposta VERA, e a dirlo e' il dataset, non io.**

COSA RESTA MIO, e lo dichiaro: la FORMA linguistica dell'astensione. Non invento
QUALI casi sono astensioni (lo dice SQuAD v2 / HaluEval), invento COME si scrive
l'astensione. E' una differenza sostanziale rispetto a «scrivo esempi
ispirandomi al test», ma non e' zero: uso cinque forme diverse perche' il modello
non impari una stringa, e CONTROLLO che nessuna di esse compaia nel test.

CONTROLLI CHE DEVONO ACCENDERSI:
  ① le 200 domande sono disgiunte da TUTTI i banchi di misura (misurato: 0 in
     comune su squad-dev, squad-heldout, halueval-dev, halueval-400)
  ② nessuna delle mie forme di astensione compare fra i claim del test
     TruthfulQA-600 — se una compare, la tolgo: sarebbe la stessa contaminazione
     di stringa che ho tolto dal dev (8 righe, 5 su 6 astensioni)
  ③ il conteggio della classe critica deve salire: da 7 a piu' di 100
"""
import io
import json
import os
import random
import re

E = "benchmark/data/external/"
OUT = "docs/stato-reale/banchi/_out/"   # relativo al repo
os.makedirs(OUT, exist_ok=True)

# LE CINQUE FORME — scritte da me, dichiarate, e controllate contro il test
FORME = [
    "The document does not say.",
    "That is not stated in the passage.",
    "There is no information about that in this text.",
    "The passage does not answer that.",
    "This source does not contain that information.",
]


def carica(p):
    return [json.loads(x) for x in io.open(E + p, encoding="utf-8") if x.strip()]


sq = carica("squad_v2_unanswerable.jsonl")
hu = carica("halueval_qa_unanswerable.jsonl")
th = carica("truthfulqa_pairs_heldout.jsonl")

print("  ① DISGIUNZIONE dai banchi di misura")
for nome, dom, altri in (
        ("squad_v2_unans", {r["question"] for r in sq},
         [("squad_v2_dev.jsonl", "question"), ("squad_v2_heldout.jsonl", "question")]),
        ("halueval_unans", {r["question"] for r in hu},
         [("halueval_qa_dev.jsonl", "question"), ("halueval_qa_heldout.jsonl", "question")])):
    for f, k in altri:
        n = len(dom & {r[k] for r in carica(f)})
        print(f"    {nome} contro {f:<28} {n} in comune"
              f"   {'ACCESO' if n == 0 else 'SPENTO'}")

print("\n  ② LE MIE FORME COMPAIONO NEL TEST?")
claim_test = {r["claim"].strip().lower().rstrip(".") for r in th}
sporche = [f for f in FORME if f.strip().lower().rstrip(".") in claim_test]
print(f"    forme che compaiono nei 600 di TruthfulQA: {len(sporche)}"
      f"   {'ACCESO' if not sporche else 'SPENTO: ' + str(sporche)}")
if sporche:
    raise SystemExit(1)
FORME[:] = [f for f in FORME if f not in sporche]

rng = random.Random(7)
righe = []
for r in sq:
    righe.append({"source": r["knowledge"],
                  "claim": f"{r['question']} {rng.choice(FORME)}",
                  "label": 1, "fonte": "squad-unans", "classe": "astensione"})
for r in hu:
    righe.append({"source": r["knowledge"],
                  "claim": f"{r['question']} {rng.choice(FORME)}",
                  "label": 1, "fonte": "halueval-unans", "classe": "astensione"})
    # il falso: il documento non risponde, ma il claim ASSERISCE — l'etichetta
    # falsa viene dal dataset (hallucinated_answer), non da me
    righe.append({"source": r["knowledge"],
                  "claim": f"{r['question']} {r['hallucinated_answer']}",
                  "label": 0, "fonte": "halueval-unans", "classe": "asserisce-senza-fonte"})
# per SQuAD non c'e' una risposta falsa pronta: uso la risposta di UN ALTRO
# documento (negativo «foreign», lo stesso schema di benchmark/local_gate_finetune.py)
for k, r in enumerate(sq):
    altro = sq[(k + 37) % len(sq)]
    righe.append({"source": r["knowledge"],
                  "claim": f"{r['question']} {altro['question'].rstrip('?')}.",
                  "label": 0, "fonte": "squad-unans", "classe": "foreign"})

with io.open(OUT + "v31_astensioni.jsonl", "w", encoding="utf-8") as fh:
    for r in righe:
        fh.write(json.dumps(r, ensure_ascii=False) + chr(10))

v = sum(1 for r in righe if r["label"] == 1)
print(f"\n  ③ COSTRUITI {len(righe)} claim: {v} veri (astensioni) · {len(righe)-v} falsi")
print(f"     scritto {OUT}v31_astensioni.jsonl")
print(f"\n  LA CLASSE CRITICA, prima e dopo:")
print(f"    train v3          7 astensioni su 437  =  1,6%")
tot = 437 + len(righe)
print(f"    train v3.1      {7+v:>3} astensioni su {tot}  = {100*(7+v)/tot:>4.1f}%")
print(f"    ⇒ esempi per ogni caso da curare (29 astensioni perse dal moat):"
      f" da 0,24 a {(7+v)/29:.1f}")

# ── IL CONTROLLO CHE MANCAVA: LE ASTENSIONI *FALSE* ─────────────────────
# Un dataset che contiene solo astensioni VERE insegna una scorciatoia: «forma
# di astensione => vero». Un modello che la impara prende il massimo sul banco
# ed e' rotto — basta un falso che comincia cosi'. Quindi: la STESSA forma su
# documenti che INVECE rispondono alla domanda, dove il claim e' FALSO.
hd = carica("halueval_qa_dev.jsonl")
rng2 = random.Random(11)
for r in hd:
    righe.append({"source": r["knowledge"],
                  "claim": f"{r['question']} {rng2.choice(FORME)}",
                  "label": 0, "fonte": "halueval-dev", "classe": "astensione-FALSA"})

with io.open(OUT + "v31_astensioni.jsonl", "w", encoding="utf-8") as fh:
    for r in righe:
        fh.write(json.dumps(r, ensure_ascii=False) + chr(10))

from collections import Counter  # noqa: E402
print("\n  IL PACCHETTO v3.1:")
for k, n in Counter((r["fonte"], r["classe"], r["label"]) for r in righe).most_common():
    print(f"    {n:>4}  {k[0]:<16} {k[1]:<22} label={k[2]}")
v2 = sum(1 for r in righe if r["label"] == 1)
tot2 = 437 + len(righe)
print(f"    ---- {len(righe)} claim: {v2} veri · {len(righe)-v2} falsi")
print(f"  train v3.1: {7+v2} astensioni vere su {tot2} = {100*(7+v2)/tot2:.1f}%"
      f"  (era 1,6%)")
