# -*- coding: utf-8 -*-
"""LA FORMA, PRIMA DELLA CAUSA — e il ponte con il fronte del 26/08.

Il 26/08 avevo misurato che aggiungere alla fonte del testo PRIVO DI SIGNIFICATO
ribalta il verdetto in modo non monotono (`docs/stato-reale/10-...md:45`):

    74→0.5 · 263→1.2 · 473→85.4 · 893→99.9 · 1733→1.0

Ieri sera la spiegazione naturale era «e' il contorno estraneo a confondere il
giudice». Il 27/08 alle 20:47 ho trovato la stessa forma dove **non c'e' nessun
contorno**: lo stesso documento reale tagliato piu' lungo, testo pertinente e
continuo, la stessa prova dentro:

    1000→0.3 · 2000→55.2 · 3000→20.8 · 4000→98.2 · 6000→99.3 · 10000→98.6 · 20000→0.2

⇒ Le due misure hanno la stessa forma — bassa, alta, bassa — ma a SCALA
diversa: il picco stava a 893 caratteri, ora sta fra 4000 e 10000. Se fosse una
periodicita' fissa in caratteri, le due scale coinciderebbero. Non coincidono.

Sette punti bastano a vedere che la curva sale e scende, non a dirne la forma.
Questo banco la campiona a passo fine e mette accanto a ogni cella la POSIZIONE
RELATIVA della prova nella fonte, che e' la variabile che si muove insieme alla
lunghezza e che nessuna delle due misure precedenti teneva separata.

CONTROLLO CHE DEVE POTER FALLIRE: ogni fonte contiene «1143» e non contiene
«9999». Senza questo non sto allungando la stessa fonte: ne sto misurando altre.

⚠️ Le celle sotto i 3000 caratteri costano ~20 secondi l'una (misurato), le
altre ~200 ms. Il banco stampa i tempi: se la soglia non si vede, e' cambiato
qualcosa nell'ambiente e va detto prima di leggere i grounding.

    python docs/stato-reale/banchi/la-forma-della-curva-a-passo-fine.py
"""

from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

DOC = Path("docs/archive/2026-05-13_FORGIA.md")
CLAIM = "Il file wake.py conta 9999 LOC."
TAGLI = [1000, 1500, 2000, 2500, 3000, 3500, 4000, 4500, 5000,
         6000, 7000, 8000, 10000, 14000, 20000]


def main() -> int:
    if not DOC.exists():
        print(f"NON RIUSCITO: {DOC} non c'e' — eseguire dalla radice del repo")
        return 1
    testo = DOC.read_text(encoding="utf-8", errors="replace")
    dove = testo.find("1143")
    if dove < 0:
        print("NON RIUSCITO: «1143» non e' nel documento")
        return 1
    print(f"  documento reale: {DOC} ({len(testo)} caratteri)")
    print(f"  la prova «1143» sta al carattere {dove}\n")

    for n in TAGLI:
        f = testo[:n]
        if "1143" not in f or "9999" in f:
            print(f"CONTROLLO CADUTO al taglio {n}: 1143={'1143' in f}, 9999={'9999' in f}")
            return 1
    print(f"  CONTROLLO retto: «1143» in tutte le {len(TAGLI)} fonti, «9999» in nessuna\n")

    from verimem.client import Memory  # noqa: PLC0415

    mem = Memory(str(Path(tempfile.mkdtemp()) / "fine.db"))

    print("  taglio   pos.prova   ground      ms   andamento")
    print("  " + "-" * 62)
    curva = []
    prec = None
    for n in TAGLI:
        t0 = time.monotonic()
        ric = mem.add(CLAIM, topic=f"fine/{n}", source=testo[:n], validate="full")
        ms = (time.monotonic() - t0) * 1000
        g = float(ric.get("grounding_score") or -1)
        pos = 100.0 * dove / n
        freccia = "" if prec is None else ("  su" if g > prec + 5 else ("  giu" if g < prec - 5 else "   ="))
        barra = "#" * int(g / 4)
        print(f"  {n:>6}   {pos:6.1f}%   {g:6.1f}  {ms:6.0f}  {freccia} {barra}")
        curva.append((n, pos, g, ms))
        prec = g

    gs = [g for _n, _p, g, _m in curva]
    alti = [(n, g) for n, _p, g, _m in curva if g >= 50]
    bassi = [(n, g) for n, _p, g, _m in curva if g < 50]
    print(f"\n  celle sopra 50: {len(alti)} su {len(curva)}  ·  sotto 50: {len(bassi)}")
    print(f"  intervallo: {min(gs):.1f} - {max(gs):.1f}")

    # quante volte la curva cambia direzione: una sola salita e discesa e' una
    # campana, molte inversioni sono un'altra cosa e vanno chiamate diversamente.
    inversioni = 0
    verso = 0
    for i in range(1, len(gs)):
        d = gs[i] - gs[i - 1]
        if abs(d) < 5:
            continue
        v = 1 if d > 0 else -1
        if verso and v != verso:
            inversioni += 1
        verso = v
    print(f"  inversioni di direzione (soglia 5 punti): {inversioni}")
    if inversioni <= 1:
        print("  ⇒ una CAMPANA: c'e' una finestra di lunghezze in cui il giudice sbaglia.")
    else:
        print("  ⇒ NON una campana: il punteggio oscilla piu' volte lungo la stessa fonte.")

    tempi_corti = [m for n, _p, _g, m in curva if n < 3000]
    tempi_lunghi = [m for n, _p, _g, m in curva if n >= 3000]
    print(f"\n  tempo sotto 3000 char: {min(tempi_corti):.0f}-{max(tempi_corti):.0f} ms")
    print(f"  tempo da 3000 in su:   {min(tempi_lunghi):.0f}-{max(tempi_lunghi):.0f} ms")
    return 0


if __name__ == "__main__":
    sys.exit(main())
