"""Unisce le etichette lette a mano (etichette_102.txt, nell'ordine k del JSON dei
96 crolli) ai 102 claim caduti, e scrive il JSON etichettato accanto al JSON dei
96. Stampa il conteggio per etichetta e per «pulito»."""
import json
import pathlib
import sys
from collections import Counter

QUI = pathlib.Path(__file__).resolve().parent
src = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else QUI / "ws3-i-96-crolli-del-giudice-sui-claim-brevi.json"
dest = src.with_name("ws3-i-102-claim-caduti-etichettati-a-mano.json")

etichette = {}
for line in (QUI / "ws3-i-102-claim-caduti-etichette-lette-a-mano.txt").read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line or line.startswith("#"):
        continue
    parti = line.split(None, 2)
    etichette[int(parti[0])] = (parti[1], parti[2] if len(parti) > 2 else "")

d = json.load(open(src, encoding="utf-8"))
out = []
k = 0
for o in d:
    for j, c in enumerate(o["caduti"]):
        k += 1
        lab, nota = etichette[k]
        out.append({"k": k, "id": o["id"], "j": j, "pulito": o["pulito"], "claim": c["claim"], "score": c["score"],
                    "intero": o["intero"], "span": o["span"], "etichetta": lab, "nota": nota})
dest.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
tot = Counter(x["etichetta"] for x in out)
pul = Counter(x["etichetta"] for x in out if x["pulito"])
print(f"{len(out)} claim caduti etichettati: {dict(tot)} · fra i puliti: {dict(pul)}")
malformati = [x for x in out if x["etichetta"] == "D" and ("frammento" in x["nota"] or "MALFORMATO" in x["nota"] or "malformato" in x["nota"])]
print(f"D per frammento malformato dalla decomposizione: {len(malformati)} — {[x['claim'][:40] for x in malformati]}")
print("scritto:", dest.name)
