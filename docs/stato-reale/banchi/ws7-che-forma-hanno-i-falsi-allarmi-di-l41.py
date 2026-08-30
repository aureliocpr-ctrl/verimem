"""I falsi allarmi di L4.1 sono rumore casuale o una CLASSE?

Segue da `LANT-80` e dal banco `ws7-quanto-sbaglia-l41-sui-fatti-che-trattiene.py`:
dei fatti che `L4.1` trattiene mentre il giudice li approva, **il 17% e' un
falso allarme** — il valore c'e', scritto alla lettera nella fonte.

Il primo esempio letto era: *«il job piu' vecchio del run 33209614102 e' partito
alle **19:29**»*, dove `L4.1` estrae **`19`**. **E' un'ORA, non una grandezza.**

⇒ E' la terza istanza della stessa famiglia in un giorno:
   `LANT-42`  i «valori assenti» erano `ValoreAssente(8.0,'08')` e `(29.0,'29')`
              = **una data** · A/B: 6/6 fermati con la data, 0/6 senza
   30/08      `00-ESAME.md` in un claim fa estrarre **`00`** = un nome di file
   qui        `19:29` fa estrarre **`19`** = un orario

⇒ 🔑 **L'ipotesi da falsificare: i falsi allarmi di L4.1 non sono rumore, sono
NUMERI DECORATIVI** — parti di date, orari, id di run, nomi di file, versioni.
Un numero che non e' la grandezza di cui il claim parla.

Se regge, il 17% ha una cura precisa invece di essere un costo diffuso.

Store in SOLA LETTURA.
"""
import re
import sqlite3
from collections import Counter

from verimem.config import CONFIG
from verimem.valore_non_nella_fonte import valori_non_nella_fonte

con = sqlite3.connect(f"file:{CONFIG.semantic_db}?mode=ro", uri=True)

#: le forme in cui un numero NON e' una grandezza. L'ordine conta: il primo che
#: matcha vince, e i pattern piu' specifici stanno prima.
DECORATIVI = [
    ("orario",       r"\d{1,2}:\d{2}"),
    ("data",         r"\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?|\d{4}-\d{2}-\d{2}"),
    ("versione",     r"\bv?\d+\.\d+(?:\.\d+)?\b"),
    ("nome di file", r"[\w-]*\d[\w-]*\.(?:py|md|json|ya?ml|txt|db)"),
    ("id lungo",     r"\b\d{8,}\b"),
    ("sha",          r"\b[0-9a-f]{7,}\b"),
]

righe = con.execute(
    "SELECT proposition, grounding_span FROM facts "
    "WHERE status='quarantined' AND grounding_score>=80 "
    "AND created_at >= strftime('%s','now') - 172800").fetchall()

forme: Counter = Counter()
grandezze: list[str] = []
for testo, fonte in righe:
    if not (testo and fonte):
        continue
    assenti = valori_non_nella_fonte(testo, fonte)
    if not assenti:
        continue                       # span troncato: escluso, vedi banco precedente
    presenti = [a.testo for a in assenti
                if re.search(rf"(?<!\d){re.escape(a.testo)}(?!\d)", fonte)]
    if not presenti:
        continue                       # L4.1 ha ragione: non e' un falso allarme
    val = presenti[0]
    #: il valore incriminato sta DENTRO una forma decorativa nel claim?
    etichetta = None
    for nome, pat in DECORATIVI:
        for m in re.finditer(pat, testo):
            if val in m.group(0) and m.group(0) != val:
                etichetta = f"{nome} ({m.group(0)!r} -> {val!r})"
                break
        if etichetta:
            break
    forme[etichetta.split(" (")[0] if etichetta else "grandezza vera"] += 1
    if etichetta:
        print(f"  DECORATIVO  {etichetta}\n     «{testo[:78]}…»")
    else:
        grandezze.append(f"{val!r} in «{testo[:70]}…»")

print(f"\n  === i falsi allarmi di L4.1, per forma del numero ===")
for nome, n in forme.most_common():
    print(f"     {n:3}  {nome}")
tot = sum(forme.values())
dec = tot - forme.get("grandezza vera", 0)
if tot:
    print(f"\n  ⇒ decorativi: {dec}/{tot} = {100*dec/tot:.0f}%")
    print("     l'ipotesi «i falsi allarmi sono numeri decorativi» "
          + ("REGGE" if dec > tot / 2 else "CADE") + " su questa popolazione")
for g in grandezze:
    print(f"     · grandezza vera fraintesa: {g}")
print("\n  ⚠️  popolazione piccola e nostra: e' un indizio sulla FORMA della cura,")
print("     non una stima del costo. E i casi con span troncato restano fuori.")
