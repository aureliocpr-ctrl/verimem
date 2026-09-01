"""I «136 numeri-claim» del README sono occorrenze: quanti sono i DISTINTI?

PERCHE'. @ws4 il 02/09 alle 00:42 ha contato **136** numeri con forma di claim
nel README e **3** nella lista auditata, e ha dichiarato lei stessa il limite:
*«IL 136 E' GONFIATO E LO DICO: sono OCCORRENZE, non numeri distinti — una riga
con due valori conta due volte, ci sono i badge…»*.

⇒ Un limite dichiarato e' un debito, e questo lo paga: se i distinti sono molti
meno, il «3 su 136 = 2,2% auditato» ha un DENOMINATORE GONFIO — la forma che il
02/09 ho gia' trovato tre volte, e che sbaglia sempre nella direzione che ci
accusa.

⚠️ NON replico il criterio di @ws4: non lo conosco. Dichiaro il MIO, e il
confronto va fatto sugli ordini di grandezza, non sul decimale.

IL MIO CRITERIO, e i suoi buchi:
  · guardo le righe FUORI dai blocchi di codice (```)
  · un «numero-claim» e' una cifra con decimale, una percentuale o una
    frazione tipo 8/10 — NON i numeri di riga, le versioni, le date
  · i DISTINTI si contano sul VALORE normalizzato, non sulla posizione
⚠️ Un valore che compare in due righe con SIGNIFICATI diversi (il 18,4% che il
02/09 ho trovato essere due grandezze senza nulla in comune) qui conta UNA
volta: **il conteggio dei distinti SOTTOSTIMA il lavoro di audit necessario**,
ed e' il limite principale di questo banco.
"""
import re
import sys
from collections import Counter
from pathlib import Path

README = Path(__file__).resolve().parents[3] / "README.md"

#: una cifra con decimale (0.87 / 29,3), una percentuale (54%), una frazione
#: (8/10). Volutamente NON prendo gli interi nudi: «3 porte» non e' un claim.
NUMERO = re.compile(r"\b\d+[.,]\d+%?\b|\b\d+%\b|\b\d+/\d+\b")
#: cio' che NON e' un claim anche se ne ha la forma
ESCLUDI = re.compile(r"^(0\.\d+\.\d+|20\d\d)$")


def main() -> int:
    if not README.exists():
        print(f"  {README} non trovato")
        return 2
    righe = README.read_text(encoding="utf-8").splitlines()

    dentro_blocco, occorrenze, per_riga = False, [], {}
    for i, r in enumerate(righe, 1):
        if r.lstrip().startswith("```"):
            dentro_blocco = not dentro_blocco
            continue
        if dentro_blocco:
            continue
        trovati = [n for n in NUMERO.findall(r) if not ESCLUDI.match(n)]
        if trovati:
            per_riga[i] = trovati
            occorrenze.extend(trovati)

    #: normalizzo: la virgola decimale e il punto sono lo stesso valore
    def _norm(n: str) -> str:
        return n.replace(",", ".")

    distinti = Counter(_norm(n) for n in occorrenze)

    print(f"  README: {len(righe)} righe · fuori dai blocchi di codice\n")
    print(f"     occorrenze con forma di numero-claim   {len(occorrenze)}")
    print(f"     valori DISTINTI                        {len(distinti)}")
    print(f"     righe che ne contengono almeno uno     {len(per_riga)}")

    ripetuti = [(v, c) for v, c in distinti.most_common() if c > 1]
    print(f"\n     valori che compaiono PIU' di una volta: {len(ripetuti)}")
    for v, c in ripetuti[:8]:
        print(f"        {v:<10} {c} volte")

    #: i sette numeri gia' auditati stanotte, per dare la copertura
    AUDITATI = {"0.87", "0.81", "0.96", "0.97", "0.90", "0.82", "35.9", "9.6",
                "15.9", "29.3", "13.3", "50.0"}
    coperti = sum(1 for v in distinti if v in AUDITATI)
    print(f"\n     di cui gia' auditati stanotte: {coperti}"
          f"  = {100*coperti/max(1,len(distinti)):.1f}% dei distinti")
    print("  ⚠️ La copertura vale per i valori, non per le AFFERMAZIONI: uno")
    print("     stesso valore in due righe puo' sostenere due claim diversi.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
