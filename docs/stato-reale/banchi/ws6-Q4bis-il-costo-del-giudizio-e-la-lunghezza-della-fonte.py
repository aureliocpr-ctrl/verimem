# -*- coding: utf-8 -*-
r"""Q4-bis: il costo di un write giudicato dipende dalla LUNGHEZZA DELLA FONTE?

Falsifica il MIO stesso numero delle 20:35 (Q4: 0,48 s a regime, 26 s di pedaggio
d'apertura), che e' misurato su fonti di poche righe. @ws5 alle 20:34 ha mostrato che
il regime vero sono documenti di migliaia di parole. Un numero di COSTO misurato fuori
dal regime vero e' vetrina quanto un numero di QUALITA'.

UNA SOLA VARIABILE, ed e' il rimedio all'errore che ho commesso tre volte oggi
(banchi con due variabili insieme): la fonte e' sempre **la stessa riga-ancora** che
sostiene il claim, seguita da N parole di `docs/BENCHMARKS.md`. Cambia N e nient'altro.
Il claim non cambia mai forma: cambia solo il nome del registro (ALFA/BETA/GAMMA), che
serve a non innescare la supersessione fra le tre ripetizioni della stessa lunghezza.

CONTROLLO CHE DEVE FALLIRE: gli stessi write **senza `source`**. Senza fonte il moat non
gira, quindi il tempo NON deve dipendere da N. Se scala anche quello, il banco misura
l'I/O e va buttato.
CONTROLLO D'ORDINE: la lunghezza piu' corta e' rifatta ALLA FINE. Se costa come
all'inizio, la crescita e' della lunghezza e non della posizione nella sequenza.
WARM-UP: due write buttati prima di misurare, perche' su questa macchina il caricamento
avviene in DUE scalini (37 -> 893 MB al 1o write, -> 1940 MB al 2o) e chi misura dal
secondo include ancora un caricamento.

REGIME: store temporaneo `Memory(path=...)` (NON `ENGRAM_DATA_DIR`, che su questa
macchina non isola) - FUORI da pytest, dove l'embedder e' uno stub SHA-256 - un solo
processo - ogni tempo stampato singolarmente, mai una media da sola.

RIPRODUCI:  python docs/stato-reale/banchi/ws6-Q4bis-il-costo-del-giudizio-e-la-lunghezza-della-fonte.py
"""
from __future__ import annotations

import time
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
LUNGHEZZE = [10, 100, 1000, 3000, 10000]
NOMI = ["ALFA", "BETA", "GAMMA"]
ANCORA = "Il registro {n} elenca le misure del progetto."


def _ram_mb() -> float:
    try:
        import psutil, os
        return psutil.Process(os.getpid()).memory_info().rss / 1e6
    except Exception:
        return float("nan")


def main() -> None:
    parole = (REPO / "docs" / "BENCHMARKS.md").read_text(encoding="utf-8").split()
    print(f"fonte: docs/BENCHMARKS.md, {len(parole)} parole")
    print(f"RAM prima di importare .......... {_ram_mb():8.0f} MB")

    from verimem.client import Memory
    mem = Memory(str(Path(tempfile.mkdtemp()) / "q4bis.db"))

    print("\n-- WARM-UP (buttati: pagano i DUE caricamenti) --")
    for i in range(2):
        t0 = time.perf_counter()
        mem.add(f"Il registro WARMUP{i} elenca le misure del progetto.",
                topic="q4bis/warmup",
                source=f"Il registro WARMUP{i} elenca le misure del progetto.")
        print(f"   warm-up #{i+1} .................. {time.perf_counter()-t0:7.2f}s"
              f"   RAM {_ram_mb():6.0f} MB")

    def giro(lunghezze, etichetta, con_source):
        print(f"\n-- {etichetta} --")
        for L in lunghezze:
            coda = " ".join(parole[:L])
            tempi = []
            for n in NOMI:
                claim = ANCORA.format(n=n)
                src = f"{claim}\n\n{coda}" if con_source else None
                t0 = time.perf_counter()
                r = mem.add(claim, topic=f"q4bis/{etichetta[:4]}-{L}-{n}", source=src)
                dt = time.perf_counter() - t0
                tempi.append(dt)
                st = (r or {}).get("status", "?")
                print(f"   {L:>6} parole  {n:<5} {dt:7.2f}s   status={st}")
            m = sum(tempi) / len(tempi)
            print(f"   {L:>6} parole  MEDIA {m:7.2f}s   min {min(tempi):.2f} "
                  f"max {max(tempi):.2f}   RAM {_ram_mb():6.0f} MB")

    giro(LUNGHEZZE, "GIUDICATI (con source)", True)
    giro(LUNGHEZZE, "CONTROLLO senza source", False)
    giro([LUNGHEZZE[0]], "CONTROLLO D'ORDINE (la piu' corta, alla fine)", True)


if __name__ == "__main__":
    main()
