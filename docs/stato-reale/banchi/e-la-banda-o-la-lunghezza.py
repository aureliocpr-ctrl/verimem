# -*- coding: utf-8 -*-
"""I VENTI SECONDI SEGUONO LA BANDA O LA LUNGHEZZA? Le due erano confuse.

Alle 21:02 ho consegnato al canale una correlazione e mi sono fermata li':
i giri lenti danno 45.6 45.6 49.2 52.7 54.2 55.2 (sette su otto nella banda
centrale) e i dodici veloci sono tutti estremi, nessuno fra 40 e 60. Ma tutte
le celle lente erano ANCHE corte: lunghezza e banda si muovevano insieme, e una
correlazione fra due variabili confuse non dice quale delle due conta.

Il 2x2 le separa. Basta un claim VERO, che sulla stessa fonte corta deve dare
un punteggio estremo invece che centrale:

              claim FALSO (9999)      claim VERO (1143)
  fonte 2000  gia' noto: 45157 ms         ?
  fonte 6000  gia' noto:   261 ms         ?

  se «2000 + vero» e' VELOCE  ⇒ e' la BANDA a costare, non la lunghezza,
     e i venti secondi sono il prezzo dell'incertezza;
  se «2000 + vero» e' LENTO   ⇒ e' la LUNGHEZZA, e la banda e' un accidente.

Le due celle gia' note le rifaccio nella STESSA esecuzione invece di citarle:
un confronto fra numeri di due processi diversi non e' un confronto.

CONTROLLO CHE DEVE POTER FALLIRE: il claim vero deve risultare ammesso e quello
falso quarantined. Se il claim «vero» non passa, non e' la cella che credo.

    python docs/stato-reale/banchi/e-la-banda-o-la-lunghezza.py
"""

from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

DOC = Path("docs/archive/2026-05-13_FORGIA.md")
VERO = "Il file wake.py conta 1143 LOC."
FALSO = "Il file wake.py conta 9999 LOC."


def main() -> int:
    if not DOC.exists():
        print(f"NON RIUSCITO: {DOC} non c'e'")
        return 1
    testo = DOC.read_text(encoding="utf-8", errors="replace")

    from verimem.client import Memory  # noqa: PLC0415

    mem = Memory(str(Path(tempfile.mkdtemp()) / "banda.db"))

    print("  fonte   claim    esito         ground      ms")
    print("  " + "-" * 48)
    celle = {}
    for n in (2000, 6000):
        for nome, prop in (("FALSO", FALSO), ("VERO ", VERO)):
            t0 = time.monotonic()
            ric = mem.add(prop, topic=f"banda/{n}/{nome.strip()}", source=testo[:n], validate="full")
            ms = (time.monotonic() - t0) * 1000
            g = float(ric.get("grounding_score") or -1)
            st = str(ric.get("status"))
            celle[(n, nome.strip())] = (st, g, ms)
            print(f"  {n:>5}   {nome}    {st:<12} {g:6.1f}  {ms:7.0f}")

    print("\nCONTROLLO il vero passa e il falso no, su entrambe le fonti:")
    male = [k for k, (st, _g, _m) in celle.items()
            if (k[1] == "VERO" and st == "quarantined") or (k[1] == "FALSO" and st != "quarantined")]
    if male:
        print(f"   CADUTO su {male}: non sono le celle che credo")
        return 1
    print("   retto")

    v2 = celle[(2000, "VERO")]
    f2 = celle[(2000, "FALSO")]
    print("\nLA DOMANDA — sulla stessa fonte corta, il vero e' veloce?")
    print(f"   2000 + FALSO (ground {f2[1]:.1f}): {f2[2]:.0f} ms")
    print(f"   2000 + VERO  (ground {v2[1]:.1f}): {v2[2]:.0f} ms")
    if v2[2] * 5 < f2[2]:
        print("   ⇒ E' LA BANDA: a parita' di lunghezza, il punteggio centrale costa")
        print("     venti secondi e quello estremo no. La lunghezza non spiega niente,")
        print("     spiega solo QUANDO il punteggio finisce al centro.")
    elif abs(v2[2] - f2[2]) < max(v2[2], f2[2]) * 0.5:
        print("   ⇒ E' LA LUNGHEZZA: stessa fonte, stesso costo, punteggi opposti.")
        print("     La correlazione con la banda che ho pubblicato e' un accidente.")
    else:
        print("   ⇒ ne' l'uno ne' l'altro in modo netto: guarda i numeri.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
