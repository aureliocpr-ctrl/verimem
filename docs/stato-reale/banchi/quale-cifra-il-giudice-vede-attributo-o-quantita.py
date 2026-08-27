# -*- coding: utf-8 -*-
"""SE NON E' LA LUNGHEZZA, E' IL TIPO DI CLAIM. Il 2x2 sulla stessa fonte.

Alle 21:30 avevo dichiarato al canale un'ipotesi: «la cifra conta sulla fonte
corta e sparisce su quella lunga». Alle 21:33 il banco della diluizione l'ha
FALSIFICATA — lo stesso claim numerico falso resta fra 0.2 e 18.9 dalla frase
nuda (52 caratteri) fino a 8018, e la quota della prova sul totale scende dal
100% allo 0.6% senza spostare il verdetto.

Restano due candidati per la differenza fra i due banchi di stasera:
il TIPO DI CLAIM e la NATURA DELLA FONTE. Questo banco tiene la fonte FISSA —
lo stesso documento reale, gli stessi 6000 caratteri — e muove solo il tipo:

  ATTRIBUTO  una proprieta' di un'entita' nominata     «wake.py conta 9999 LOC»
  QUANTITA'  quanti elementi ci sono in un insieme     «sono stati letti 7 file»

Entrambi falsi, entrambi con una cifra che la fonte non contiene. Se l'attributo
prende un punteggio alto e la quantita' no, il giudice guarda l'ENTITA' nominata
e non l'insieme, e questo spiega perche' i miei due banchi dicevano cose opposte.

CONTROLLO CHE DEVE POTER FALLIRE: la cifra di ogni claim falso NON deve stare
nella fonte, e quella dei claim veri SI'. Il banco lo verifica e si ferma se no.

    python docs/stato-reale/banchi/quale-cifra-il-giudice-vede-attributo-o-quantita.py
"""

from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path

DOC = Path("docs/archive/2026-05-13_FORGIA.md")

# (etichetta, claim, cifra del claim, deve stare nella fonte?)
CASI = [
    ("attributo VERO  ", "Il file wake.py conta 1143 LOC.", "1143", True),
    ("attributo FALSO ", "Il file wake.py conta 9999 LOC.", "9999", False),
    ("quantita' VERA  ", "Sono stati letti 3 file.", "3", True),
    ("quantita' FALSA ", "Sono stati letti 77 file.", "77", False),
]


def main() -> int:
    if not DOC.exists():
        print(f"NON RIUSCITO: {DOC} non c'e'")
        return 1
    fonte = DOC.read_text(encoding="utf-8", errors="replace")[:6000]
    numeri = set(re.findall(r"\d+", fonte))
    print(f"  fonte: primi 6000 caratteri di {DOC}")

    for eti, _prop, cifra, dentro in CASI:
        c_e = cifra in numeri
        if c_e != dentro:
            print(f"CONTROLLO CADUTO su «{eti.strip()}»: «{cifra}» nella fonte = {c_e},")
            print(f"   il banco si aspettava {dentro}. Non e' il caso che credo.")
            return 1
    print("  CONTROLLO retto: le cifre dei veri sono nella fonte, quelle dei falsi no\n")

    from verimem.client import Memory  # noqa: PLC0415

    mem = Memory(str(Path(tempfile.mkdtemp()) / "tipo.db"))

    print("  caso                 esito         ground")
    print("  " + "-" * 46)
    r = {}
    for eti, prop, _c, _d in CASI:
        ric = mem.add(prop, topic=f"tipo/{eti.strip().replace(chr(32), '_')}", source=fonte, validate="full")
        g = float(ric.get("grounding_score") or -1)
        st = str(ric.get("status"))
        r[eti.strip()] = (st, g)
        print(f"  {eti}    {st:<12} {g:6.1f}  {'#' * int(max(g, 0) / 4)}")

    af = r["attributo FALSO"][1]
    qf = r["quantita' FALSA"][1]
    print(f"\n  LA DOMANDA — a parita' di fonte, il giudice vede la cifra di un")
    print("  ATTRIBUTO o quella di una QUANTITA'?")
    print(f"     attributo FALSO : {af:6.1f}")
    print(f"     quantita' FALSA : {qf:6.1f}")
    if af - qf > 40:
        print(f"  ⇒ l'attributo falso sta {af - qf:.1f} punti sopra la quantita' falsa.")
        print("    Il giudice controlla la cifra quando conta gli elementi di un")
        print("    insieme, e non la controlla quando e' la proprieta' di un'entita'")
        print("    che la fonte nomina. La differenza fra i miei due banchi e' questa,")
        print("    non la lunghezza.")
    elif qf - af > 40:
        print("  ⇒ rovesciato rispetto all'attesa: guarda i numeri e rifai il disegno.")
    else:
        print(f"  ⇒ i due stanno vicini ({abs(af - qf):.1f} punti): il tipo di claim non")
        print("    spiega la differenza, e resta in piedi solo la natura della fonte.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
