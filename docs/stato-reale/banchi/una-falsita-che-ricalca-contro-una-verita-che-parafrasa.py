# -*- coding: utf-8 -*-
"""IL PONTE FRA IL FRONTE DI ws1 E IL MIO — e il caso che li mette contro.

@ws1 alle 21:20: «il moat non misura l'implicazione, misura la CITAZIONE».
A/B a variabile singola: stessa fonte, stesso fatto, e la parafrasi prende 5.54
mentre la citazione prende 99.95.

Nel mio dossier ⑩ del 26/08 avevo pero' ESCLUSO la sovrapposizione lessicale
come spiegazione del ribaltamento, misurandola con tre grandezze diverse. Le due
cose possono convivere solo se «citazione» NON si riduce a «quante parole
condivise»: allora il test giusto non e' misurare la sovrapposizione, e' mettere
le due proprieta' in CONFLITTO su celle costruite apposta.

Quattro claim sulla stessa fonte, incrociando VERO/FALSO con RICALCA/PARAFRASA:

    A  vero  + ricalca    «Il file wake.py conta 1143 LOC.»
    B  FALSO + ricalca    «Il file wake.py conta 9999 LOC.»
    C  vero  + parafrasa  «Il modulo di risveglio e' lungo poco piu' di mille righe.»
    D  vero  + cita       «La riga dice: wake.py (1143 LOC).»

La domanda che decide: **B batte C?** Se una falsita' che ricalca prende piu' di
una verita' che parafrasa, la tesi di ws1 regge sul mio terreno e il difetto e'
piu' grave di entrambi i referti presi da soli — perche' il verso e' invertito
proprio dove il prodotto serve (nessun avvocato ricopia una riga di contratto).

Se invece C sta sopra B, la tesi non si estende a questa famiglia e va detto.

CONTROLLO CHE DEVE POTER FALLIRE: A deve essere ammesso e B fermato. Sono le due
celle di cui conosco l'esito; se cambiano, non e' il banco che credo.

    python docs/stato-reale/banchi/una-falsita-che-ricalca-contro-una-verita-che-parafrasa.py
"""

from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

DOC = Path("docs/archive/2026-05-13_FORGIA.md")
CLAIM = [
    ("A vero  + ricalca ", "Il file wake.py conta 1143 LOC."),
    ("B FALSO + ricalca ", "Il file wake.py conta 9999 LOC."),
    ("C vero  + parafrasa", "Il modulo di risveglio e' lungo poco piu' di mille righe."),
    ("D vero  + cita    ", "La riga dice: wake.py (1143 LOC)."),
]


def main() -> int:
    if not DOC.exists():
        print(f"NON RIUSCITO: {DOC} non c'e'")
        return 1
    fonte = DOC.read_text(encoding="utf-8", errors="replace")[:6000]
    if "1143" not in fonte:
        print("NON RIUSCITO: la fonte non contiene 1143")
        return 1
    print(f"  fonte: primi 6000 caratteri di {DOC}, «1143» presente\n")

    from verimem.client import Memory  # noqa: PLC0415

    mem = Memory(str(Path(tempfile.mkdtemp()) / "ponte.db"))

    print("  claim                 esito         ground       ms")
    print("  " + "-" * 52)
    r = {}
    for eti, prop in CLAIM:
        t0 = time.monotonic()
        ric = mem.add(prop, topic=f"ponte/{eti.strip()[0]}", source=fonte, validate="full")
        ms = (time.monotonic() - t0) * 1000
        g = float(ric.get("grounding_score") or -1)
        st = str(ric.get("status"))
        r[eti.strip()[0]] = (st, g)
        print(f"  {eti}   {st:<12} {g:6.1f}  {ms:7.0f}")

    print("\nCONTROLLO A ammesso e B fermato:")
    if r["A"][0] == "quarantined" or r["B"][0] != "quarantined":
        print(f"   CADUTO — A={r['A'][0]}, B={r['B'][0]}: non e' il banco che credo")
        return 1
    print(f"   retto — A {r['A'][0]}, B {r['B'][0]}")

    print("\nLA DOMANDA — una falsita' che RICALCA batte una verita' che PARAFRASA?")
    gb, gc = r["B"][1], r["C"][1]
    print(f"   B falso  + ricalca  : {gb:6.1f}   ({r['B'][0]})")
    print(f"   C vero   + parafrasa: {gc:6.1f}   ({r['C'][0]})")
    if gb > gc:
        print(f"   ⇒ SI, di {gb - gc:.1f} punti. La tesi di ws1 regge su questa famiglia:")
        print("     il verso e' invertito proprio dove il prodotto serve, perche'")
        print("     chi legge un contratto o un referto NON ricopia una riga.")
    else:
        print(f"   ⇒ NO: la verita' parafrasata sta {gc - gb:.1f} punti sopra la falsita'")
        print("     che ricalca. La tesi non si estende a questa famiglia, e va detto.")
    print(f"\n   per riferimento, D vero + cita: {r['D'][1]:.1f} ({r['D'][0]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
