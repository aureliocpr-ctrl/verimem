# -*- coding: utf-8 -*-
r"""Q4-ter: fin DOVE arriva il giudice dentro una fonte lunga?

NASCE DA UN RISULTATO CHE FALSIFICA LA MIA IPOTESI (Q4-bis, 20:41). Mi aspettavo che il
costo di un write giudicato crescesse con la lunghezza della fonte. E' PIATTO: 0,19 s a
100 parole, 0,13 s a 10.000. Ma nello stesso output c'e' un dato che il costo spiega:

    100   parole   grounding = 99.98370361328125 / 99.97803497314453 / 99.97998809814453
    1000  parole   grounding = 99.02900695800781 / 99.08013916015625 / 99.20374298095703
    3000  parole   grounding = 99.02900695800781 / 99.08013916015625 / 99.20374298095703
    10000 parole   grounding = 99.02900695800781 / 99.08013916015625 / 99.20374298095703

**Identici bit per bit a 1000, 3000 e 10000 parole.** Se il giudice leggesse davvero
diecimila parole, il punteggio cambierebbe e il costo pure. Non cambia ne' l'uno ne'
l'altro ⇒ IPOTESI: **la fonte viene troncata, e cio' che sta oltre non entra nel
giudizio.**

PREDIZIONE DICHIARATA PRIMA DI ESEGUIRE (se e' sbagliata, l'ipotesi cade):
  · ancora in TESTA -> grounding alto a ogni lunghezza (gia' osservato)
  · ancora in CODA  -> grounding alto finche' la fonte e' corta, **CROLLO** appena la
    lunghezza supera la finestra, perche' l'ancora finisce fuori.
  Se anche in CODA il grounding resta alto a 3000 parole, **NON c'e' troncamento e
  l'ipotesi e' falsa**: la spiegazione del costo piatto sara' un'altra.

CONTROLLO DI DETERMINISMO: una cella e' ripetuta. Su una funzione deterministica la
ripetizione non aggiunge informazione, ma questo va MOSTRATO, non assunto.
A/B NELLA STESSA ESECUZIONE: testa e coda sono misurate nello stesso processo, sulla
stessa build, sullo stesso store ⇒ immune alla deriva dell'albero.

REGIME: `Memory(path=...)` su store temporaneo · FUORI da pytest · un processo ·
fonte reale `docs/BENCHMARKS.md` · claim invariato, cambia SOLO dove sta l'ancora.

RIPRODUCI:  python docs/stato-reale/banchi/ws6-Q4ter-la-finestra-del-giudizio.py
"""
from __future__ import annotations

import time
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
LUNGHEZZE = [50, 100, 200, 300, 500, 700, 1000, 3000]
ANCORA = "Il registro {n} elenca le misure del progetto."


def main() -> None:
    parole = (REPO / "docs" / "BENCHMARKS.md").read_text(encoding="utf-8").split()
    from verimem.client import Memory
    mem = Memory(str(Path(tempfile.mkdtemp()) / "q4ter.db"))

    for i in range(2):  # warm-up: due caricamenti, entrambi buttati
        mem.add(f"Il registro WARMUP{i} elenca le misure del progetto.",
                topic="q4ter/warmup",
                source=f"Il registro WARMUP{i} elenca le misure del progetto.")

    def cella(L, dove, n):
        claim = ANCORA.format(n=n)
        coda = " ".join(parole[:L])
        src = f"{claim}\n\n{coda}" if dove == "TESTA" else f"{coda}\n\n{claim}"
        t0 = time.perf_counter()
        r = mem.add(claim, topic=f"q4ter/{dove}-{L}-{n}", source=src)
        dt = time.perf_counter() - t0
        g = (r or {}).get("grounding", (r or {}).get("grounding_score"))
        return dt, g, (r or {}).get("status", "?"), (r or {}).get("warnings")

    print(f"{'parole':>7}  {'ancora in TESTA':>34}   {'ancora in CODA':>34}")
    print(f"{'':>7}  {'grounding':>18} {'s':>6} {'st':>8}   "
          f"{'grounding':>18} {'s':>6} {'st':>8}")
    for L in LUNGHEZZE:
        dt_t, g_t, st_t, _ = cella(L, "TESTA", "ALFA")
        dt_c, g_c, st_c, _ = cella(L, "CODA", "BETA")
        gt = f"{g_t:.6f}" if isinstance(g_t, (int, float)) else str(g_t)
        gc = f"{g_c:.6f}" if isinstance(g_c, (int, float)) else str(g_c)
        print(f"{L:>7}  {gt:>18} {dt_t:6.2f} {str(st_t)[:8]:>8}   "
              f"{gc:>18} {dt_c:6.2f} {str(st_c)[:8]:>8}")

    print("\n-- CONTROLLO DI DETERMINISMO: la stessa cella due volte --")
    for k in range(2):
        dt, g, st, _ = cella(1000, "TESTA", "ALFA")
        gg = f"{g:.12f}" if isinstance(g, (int, float)) else str(g)
        print(f"   ripetizione #{k+1}: grounding={gg}  {dt:.2f}s")


if __name__ == "__main__":
    main()
