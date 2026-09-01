"""Tre miei script contano il registro e danno tre numeri: 673, 695, 605.

PERCHE'. Porto in giro numeri di STATO del registro («228 rossi su 673»,
«35 load-bearing su 695»). Il 01/09 alle 20:22 mi sono accorta che i tre
righelli che uso danno tre popolazioni diverse dello STESSO file. Un rapporto
il cui denominatore dipende da quale script lo stampa non e' confrontabile con
se stesso — ed e' la lezione «il denominatore si muove», che ho gia' pagato.

NON cerco «quello giusto»: cerco di sapere COSA scarta ciascuno, perche' un
filtro puo' essere corretto per il suo scopo e sbagliato come denominatore.
"""
import re
import sys
from pathlib import Path

ESAME = Path("docs/stato-reale/00-ESAME.md")
COLONNE = re.compile(r"(?<!\\)\|")
ID = re.compile(r"\s*((?:LANT|W\d)-\d+[a-z]?)\s*$")


def main() -> int:
    if not ESAME.exists():
        print(f"  {ESAME} non trovato (esegui dalla radice del repo)")
        return 2
    righe = ESAME.read_text(encoding="utf-8").splitlines()

    #: i tre filtri, scritti come li applicano i tre script
    def apre(r: str) -> bool:
        return r.startswith("| ")

    def chiude(r: str) -> bool:
        return r.rstrip().endswith("|")

    def con_id(r: str) -> bool:
        c = COLONNE.split(r)
        return len(c) > 1 and bool(ID.match(c[1]))

    def dieci(r: str) -> bool:
        return len(COLONNE.split(r)) >= 10

    largo = [r for r in righe if apre(r) and con_id(r)]
    medio = [r for r in righe if apre(r) and con_id(r) and chiude(r)]
    stretto = [r for r in righe if apre(r) and con_id(r) and chiude(r) and dieci(r)]

    print(f"  righe che aprono con la barra e portano un id:  {len(largo)}")
    print(f"     + devono CHIUDERE con la barra:              {len(medio)}"
          f"   (scarta {len(largo)-len(medio)})")
    print(f"     + devono avere >= 10 colonne:                {len(stretto)}"
          f"   (scarta {len(medio)-len(stretto)})")

    #: chi cade a ogni gradino, con l'id: e' il dato che rende il numero
    #: verificabile invece che da credere
    persi_chiusura = [COLONNE.split(r)[1].strip() for r in largo if r not in medio]
    persi_colonne = [COLONNE.split(r)[1].strip() for r in medio if r not in stretto]
    if persi_chiusura:
        print(f"\n  NON chiudono con la barra ({len(persi_chiusura)}): "
              f"{', '.join(persi_chiusura[:14])}")
        print("     ⇒ sono celle su PIU' RIGHE: il testo continua sotto.")
    if persi_colonne:
        print(f"\n  chiudono ma hanno < 10 colonne ({len(persi_colonne)}): "
              f"{', '.join(persi_colonne[:14])}")
        print("     ⇒ celle con meno campi del formato: incomplete, non rotte.")

    print("\n  ⇒ i tre numeri non sono in disaccordo: sono TRE POPOLAZIONI.")
    print("    Chi pubblica un rapporto sul registro dica QUALE usa, perche'")
    print("    lo stesso conteggio su denominatori diversi da' percentuali")
    print("    diverse — e la differenza qui non e' piccola.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
