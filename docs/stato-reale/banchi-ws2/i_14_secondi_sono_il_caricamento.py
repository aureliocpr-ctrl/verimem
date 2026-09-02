"""I 14 secondi sono il CARICAMENTO del giudice, o il giudizio?

La differenza decide se esiste una cura. Se e' il caricamento, si paga UNA volta
per processo e la cura e' la stessa gia' applicata alle embedding (un daemon
caldo, che `doctor` dichiara: «shared encode daemon warm on :51170»). Se e' il
giudizio, i 14 s sono il prezzo del prodotto e la promessa dei 2 secondi va
riscritta, non curata.

📌 O1 MEMORIA-FIRST — la traccia c'era gia', in MEMORY.md:
   «Più `verimem save` in UN processo via `verimem.cli.main` con `sys.argv`:
    il giudice si carica una volta sola.»
   Quella riga e' un accorgimento che ci siamo dati NOI per i nostri script.
   Qui la verifico al livello del prodotto e chiedo un'altra cosa: se vale per
   noi, perche' l'utente la paga a ogni comando?

QUATTRO SCRITTURE NELLO STESSO PROCESSO, cronometrate una per una.
PREDIZIONE: la prima ~14 s, le altre tre sotto il secondo. Se costano tutte
uguale, e' il giudizio e la mia ipotesi cade.
"""
from __future__ import annotations

import os
import pathlib
import sys
import tempfile
import time

VENV = pathlib.Path(sys.argv[1])
#: si esegue DENTRO il venv: il punto e' misurare la copia installata
sys.path.insert(0, str(VENV / "Lib" / "site-packages"))
CASA = pathlib.Path(tempfile.mkdtemp(prefix="carica_una_volta_"))
for k in list(os.environ):
    if k.startswith(("HIPPO_", "ENGRAM_", "VERIMEM_")):
        del os.environ[k]
os.environ["HIPPO_DATA_DIR"] = str(CASA / "dati")

from verimem.client import Memory  # noqa: E402

SORG = ("Verbale del turno di notte: il contatore del reparto nord ha registrato "
        "{n} pezzi, controfirmato dal capoturno Bianchi.")
m = Memory(pathlib.Path(os.environ["HIPPO_DATA_DIR"]) / "m.db")

print(f"  verimem da: {pathlib.Path(Memory.__module__ and __import__('verimem').__file__).parent}")
for i in range(4):
    t0 = time.time()
    m.add(f"Il reparto nord ha registrato {600+i} pezzi.",
          topic=f"carica/g{i}", source=SORG.format(n=600+i))
    print(f"    scrittura {i+1}   {time.time()-t0:6.2f}s")
