"""Quante righe del registro hanno piu' colonne del canonico, e cosa slitta.

PERCHE'. Il 01/09 alle 20:16 ho trovato che le 366 righe firmate distribuiscono
la firma su DODICI indici di colonna diversi. Il mio `celle_load_bearing.py` la
cercava in `[6]` e ne vedeva **1 su 35**; cercandola nella riga intera sono
**18 su 35**. ⇒ Avevo consegnato a @lead-audit un registro molto piu' fragile
di quello che e'.

L'IPOTESI DA FALSIFICARE. Le barre extra stanno DENTRO il verdetto (che e' la
colonna lunga). Se e' vero:
  · le colonne 0..6 reggono — `[6]` e' il verdetto TRONCATO alla prima barra,
    e il simbolo di stato sta in TESTA, quindi i conteggi di stato sopravvivono;
  · tutto cio' che viene DOPO slitta: autrice `[7]`, regime, firma.
Se invece le barre extra stanno PRIMA della 6, allora slitta anche il verdetto
e ogni conteggio di stato del registro e' sbagliato.

Le due previsioni sono DIVERSE e distinguibili: e' quello che rende questo un
banco e non un'illustrazione.

CONTROLLO. Stampo le due popolazioni — righe canoniche e righe lunghe — perche'
sui soli casi rotti ogni criterio sembra ottimo.
"""
import re
import sys
from collections import Counter
from pathlib import Path

ESAME = Path("docs/stato-reale/00-ESAME.md")
COLONNE = re.compile(r"(?<!\\)\|")
ID = re.compile(r"\s*((?:LANT|W\d)-\d+[a-z]?)\s*$")
#: il simbolo di stato, che per convenzione sta in TESTA al verdetto
SIMBOLO = re.compile(r"[🔴🟢🟡⛔🚫📊]")
AUTRICE = re.compile(r"^\s*(?:@?(?:ws\d|lead-audit|Lanterna|Galileo)|\?)")


def main() -> int:
    if not ESAME.exists():
        print(f"  {ESAME} non trovato (esegui dalla radice del repo)")
        return 2

    righe = {}
    for r in ESAME.read_text(encoding="utf-8").splitlines():
        if not r.startswith("| ") or not r.rstrip().endswith("|"):
            continue
        c = COLONNE.split(r)
        if len(c) < 10:
            continue
        m = ID.match(c[1])
        if m:
            righe[m.group(1)] = c

    n_col = Counter(len(c) for c in righe.values())
    canonico = n_col.most_common(1)[0][0]
    lunghe = {k: c for k, c in righe.items() if len(c) > canonico}

    print(f"  {len(righe)} celle · numero di colonne CANONICO = {canonico}")
    print(f"  distribuzione: {dict(sorted(n_col.items()))}")
    print(f"  righe con PIU' colonne del canonico: {len(lunghe)}"
          f"  = {100*len(lunghe)/len(righe):.1f}%\n")

    #: --- la previsione: il simbolo di stato sopravvive in [6]?
    def _quota(pop: dict, idx: int, rx: re.Pattern) -> str:
        if not pop:
            return "  (popolazione vuota)"
        ok = sum(1 for c in pop.values() if len(c) > idx and rx.search(c[idx]))
        return f"{ok}/{len(pop)} = {100*ok/len(pop):.1f}%"

    canon = {k: c for k, c in righe.items() if len(c) == canonico}
    print("  ENTRAMBE le popolazioni, sullo stesso indice fisso:\n")
    print(f"     simbolo di stato in [6]   canoniche {_quota(canon, 6, SIMBOLO)}")
    print(f"                               LUNGHE    {_quota(lunghe, 6, SIMBOLO)}")
    print(f"     autrice in [7]            canoniche {_quota(canon, 7, AUTRICE)}")
    print(f"                               LUNGHE    {_quota(lunghe, 7, AUTRICE)}")

    #: dove cade l'autrice nelle righe lunghe, se non e' in [7]
    dove = Counter()
    for c in lunghe.values():
        for i, x in enumerate(c):
            if AUTRICE.match(x) and i >= 7:
                dove[i] += 1
                break
    if dove:
        print(f"\n     nelle LUNGHE l'autrice cade su: {dict(sorted(dove.items()))}")
    print("\n  ⇒ se il primo numero regge e il secondo no, l'ipotesi TIENE:")
    print("    le barre extra stanno dentro il verdetto, i conteggi di STATO")
    print("    sopravvivono e tutto cio' che viene DOPO slitta.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
