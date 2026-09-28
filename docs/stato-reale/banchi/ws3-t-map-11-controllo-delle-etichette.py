"""Il controllo che puo' falsificare il MIO numero, fatto PRIMA di pubblicarlo.

Nel giro su HaluEval dev, quattro «invenzioni» hanno preso 99,8-99,98 — come i
fatti detti alla lettera. Due letture possibili:
  (a) il giudice sbaglia su invenzioni plausibili  -> il mio reperto;
  (b) quelle frasi il contesto LE DICE quasi alla lettera, e sono sbagliate solo
      come RISPOSTA ALLA DOMANDA -> allora l'etichetta «non detto» e' mia e
      falsa, e il numero mi sta dando ragione per il motivo sbagliato.

Nessun modello qui: solo il testo. Per ogni item stampo quanta parte delle
parole di contenuto della frase «inventata» compare nel contesto.

    python ws3_controlla_le_etichette.py <wt> --n 12
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re

VUOTE = {"the", "a", "an", "of", "in", "on", "at", "and", "or", "is", "are",
         "was", "were", "be", "been", "to", "for", "by", "with", "that",
         "this", "it", "as", "from", "has", "have", "had", "both", "his",
         "her", "their", "its", "he", "she", "they", "who", "which"}


def parole(t: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9']+", (t or "").lower())
            if w not in VUOTE and len(w) > 1]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("wt")
    ap.add_argument("--n", type=int, default=12)
    a = ap.parse_args()
    wt = pathlib.Path(a.wt).resolve()
    p = wt / "benchmark" / "data" / "external" / "halueval_qa_dev.jsonl"
    righe = [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()][: a.n]

    print(f"== {len(righe)} item di dev — quanta parte della frase INVENTATA e' gia' nel contesto")
    alte = []
    for i, r in enumerate(righe):
        ctx = set(parole(r.get("knowledge", "")))
        inv = parole(r.get("hallucinated_answer", ""))
        if not inv:
            continue
        dentro = [w for w in inv if w in ctx]
        cop = len(dentro) / len(inv)
        alte.append((cop, i, r.get("hallucinated_answer", "")[:80]))
        print(f"  #{i:02d} copertura {100*cop:5.1f}%  {r.get('hallucinated_answer','')[:78]}")
    print()
    print("== i tre casi con la copertura piu' alta, per esteso")
    for cop, i, _ in sorted(alte, reverse=True)[:3]:
        r = righe[i]
        print(f"--- #{i:02d} copertura {100*cop:.1f}%")
        print(f"    DOMANDA:   {r.get('question','')[:150]}")
        print(f"    GIUSTA:    {r.get('right_answer','')[:150]}")
        print(f"    INVENTATA: {r.get('hallucinated_answer','')[:150]}")
        print(f"    CONTESTO:  {r.get('knowledge','')[:400]}")


if __name__ == "__main__":
    main()
