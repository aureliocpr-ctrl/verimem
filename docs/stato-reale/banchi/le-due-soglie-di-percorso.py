# -*- coding: utf-8 -*-
"""LE DUE SOGLIE — perche' «oscilla» era ancora la parola sbagliata.

Il campionamento a passo fine (27/08, 20:54) ha dato questo, sullo stesso
documento tagliato piu' lungo e con la stessa prova dentro:

    1000  0.3 (21153 ms) · 1500 52.7 (24333) · 2000 55.2 (22218) · 2500 45.6 (18208)
    3000 20.8   (203 ms) · 3500 88.1   (100) · 4000 98.2   (220) · 6000 99.3    (94)
    8000 99.5    (109 ms) · 10000 98.6  (93) · 14000  0.2    (95) · 20000  0.2  (111)

Il punto che cambia la lettura non e' il grounding: e' il TEMPO. Fra 2500 e 3000
caratteri passa da 18208 ms a 203 ms — novanta volte piu' veloce con piu' testo.
Un giudizio che cambia di scala cosi' non e' lo stesso giudizio piu' o meno
sicuro: sono due strade diverse, e la lunghezza sceglie quale.

⇒ Se sono strade, i confini sono NETTI e si trovano per bisezione. Se invece il
tempo scende gradualmente, non ci sono due strade e questa lettura cade — ed e'
il modo in cui questo banco puo' fallire.

Due zone da stringere:
  A) fra 2500 e 3000 caratteri, dove salta il tempo;
  B) fra 10000 e 14000, dove il grounding crolla da 98.6 a 0.2 senza gradualita'.

CONTROLLO CHE DEVE POTER FALLIRE: ogni fonte contiene «1143» e non «9999».

    python docs/stato-reale/banchi/le-due-soglie-di-percorso.py
"""

from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

DOC = Path("docs/archive/2026-05-13_FORGIA.md")
CLAIM = "Il file wake.py conta 9999 LOC."
ZONA_A = [2500, 2600, 2700, 2800, 2900, 3000]
ZONA_B = [10000, 11000, 12000, 13000, 14000]


def main() -> int:
    if not DOC.exists():
        print(f"NON RIUSCITO: {DOC} non c'e'")
        return 1
    testo = DOC.read_text(encoding="utf-8", errors="replace")
    for n in ZONA_A + ZONA_B:
        f = testo[:n]
        if "1143" not in f or "9999" in f:
            print(f"CONTROLLO CADUTO al taglio {n}")
            return 1
    print(f"  CONTROLLO retto su tutte le {len(ZONA_A) + len(ZONA_B)} fonti")

    from verimem.client import Memory  # noqa: PLC0415

    mem = Memory(str(Path(tempfile.mkdtemp()) / "soglie.db"))

    def giro(tagli: list[int], titolo: str) -> list[tuple[int, float, float]]:
        print(f"\n  {titolo}")
        print("  taglio   ground      ms")
        print("  " + "-" * 32)
        out = []
        for n in tagli:
            t0 = time.monotonic()
            ric = mem.add(CLAIM, topic=f"soglie/{n}", source=testo[:n], validate="full")
            ms = (time.monotonic() - t0) * 1000
            g = float(ric.get("grounding_score") or -1)
            print(f"  {n:>6}   {g:6.1f}  {ms:6.0f}")
            out.append((n, g, ms))
        return out

    a = giro(ZONA_A, "ZONA A — dove salta il tempo")
    b = giro(ZONA_B, "ZONA B — dove crolla il grounding")

    print("\n  ── ZONA A: il tempo scende di colpo o gradualmente?")
    salti_a = [
        (a[i - 1][0], a[i][0], a[i - 1][2], a[i][2])
        for i in range(1, len(a))
        if a[i - 1][2] > 5 * a[i][2] or a[i][2] > 5 * a[i - 1][2]
    ]
    if len(salti_a) == 1:
        x, y, ta, tb = salti_a[0]
        print(f"     UN SOLO salto, fra {x} e {y} caratteri: {ta:.0f} ms -> {tb:.0f} ms")
        print("     ⇒ e' un confine, non una discesa: la lunghezza sceglie la strada.")
    elif not salti_a:
        print("     nessun salto di fattore 5: la lettura «due strade» CADE qui.")
    else:
        print(f"     {len(salti_a)} salti: non e' un confine unico, e va detto.")
        for x, y, ta, tb in salti_a:
            print(f"       {x} -> {y}: {ta:.0f} -> {tb:.0f} ms")

    print("\n  ── ZONA B: il grounding crolla di colpo o gradualmente?")
    salti_b = [
        (b[i - 1][0], b[i][0], b[i - 1][1], b[i][1])
        for i in range(1, len(b))
        if abs(b[i][1] - b[i - 1][1]) > 40
    ]
    if len(salti_b) == 1:
        x, y, ga, gb = salti_b[0]
        print(f"     UN SOLO crollo, fra {x} e {y} caratteri: {ga:.1f} -> {gb:.1f}")
        print("     ⇒ un secondo confine, e il tempo non lo accompagna.")
    elif not salti_b:
        print("     nessun crollo sopra 40 punti: la discesa e' graduale.")
    else:
        print(f"     {len(salti_b)} crolli:")
        for x, y, ga, gb in salti_b:
            print(f"       {x} -> {y}: {ga:.1f} -> {gb:.1f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
