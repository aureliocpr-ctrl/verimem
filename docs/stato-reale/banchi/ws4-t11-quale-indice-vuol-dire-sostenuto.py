"""T1.1 passo 2 — QUALE indice significa «sostenuto»? Determinato, non indovinato.

`config.json` di FactCG ha `id2label: None` e `num_labels: 0`: la mappatura NON
e' dichiarata. Indovinarla sarebbe il quarto errore della giornata dello stesso
tipo (riscrivere a memoria invece di verificare), quindi la si MISURA con quattro
coppie il cui esito e' ovvio:

  entailed:      «Paris is the capital of France»  ->  «Paris is in France»
                 «The suite finished in 42 seconds» -> «The suite took 42 seconds»
  contraddette:  «Paris is the capital of France»  ->  «Paris is the capital of Italy»
                 «The suite finished in 42 seconds» -> «The suite finished in 4200 seconds»

CONTROLLO CHE DEVE ACCENDERSI: lo stesso indice deve vincere su ENTRAMBE le
entailed e perdere su ENTRAMBE le contraddette. Se non succede, la mappatura non
e' determinata e non si passa all'inferenza.
"""
import os
import sys

os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS", "1")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

import torch  # noqa: E402
from transformers import AutoModelForSequenceClassification, AutoTokenizer  # noqa: E402

M = "yaxili96/FactCG-DeBERTa-v3-Large"
print(f"  carico {M} su CPU…")
tok = AutoTokenizer.from_pretrained(M)
mod = AutoModelForSequenceClassification.from_pretrained(M)
mod.eval()
n = mod.config.num_labels
print(f"  num_labels dal MODELLO (non dalla config json): {n}")

COPPIE = [
    ("Paris is the capital of France.", "Paris is in France.", True),
    ("The suite finished in 42 seconds.", "The suite took 42 seconds.", True),
    ("Paris is the capital of France.", "Paris is the capital of Italy.", False),
    ("The suite finished in 42 seconds.", "The suite finished in 4200 seconds.", False),
]

vincitori = []
print(f"\n  {'premessa -> ipotesi':<62} {'atteso':8} probabilita'")
for prem, ipo, atteso in COPPIE:
    with torch.no_grad():
        x = tok(prem, ipo, return_tensors="pt", truncation=True, max_length=512)
        p = torch.softmax(mod(**x).logits[0], dim=-1).tolist()
    vinc = max(range(len(p)), key=lambda i: p[i])
    vincitori.append((atteso, vinc, p))
    etichetta = "ENTAILED" if atteso else "CONTRAD."
    print(f"  {(prem[:28] + ' -> ' + ipo[:28]):<62} {etichetta:8} "
          f"{[round(v, 3) for v in p]}  vince {vinc}")

ent = {v for a, v, _ in vincitori if a}
con = {v for a, v, _ in vincitori if not a}
print()
if len(ent) == 1 and len(con) == 1 and ent != con:
    idx = ent.pop()
    print(f"  CONTROLLO ACCESO: l'indice {idx} vince su entrambe le entailed e")
    print(f"  perde su entrambe le contraddette => SUPPORTED = indice {idx}")
    sys.exit(0)
print(f"  CONTROLLO SPENTO: entailed vincono {ent}, contraddette {con}")
print("  => la mappatura NON e' determinata: non si passa all'inferenza")
sys.exit(1)
