r"""`--as-of` naviga una CATENA di supersessioni, o si ferma al primo anello?

Chiude il limite che avevo dichiarato io nella riga 53 del registro: la' `--as-of` era
verificato su UNA supersessione (due fatti), e ci avevo scritto «non dice nulla sulle
catene lunghe». Una catena e' il caso reale: un valore che evolve tre volte e' normale in
un magazzino, in un referto, in un prezzo.

DISEGNO: tre scritture successive dello stesso valore (4141 -> 5252 -> 6363), stesso
topic, tre istanti marcati fra l'una e l'altra.
  `--as-of` fra A e B -> deve dare A · fra B e C -> deve dare B · dopo C -> deve dare C

DUE CONTROLLI, dichiarati prima:
  ① i tre istanti devono dare TRE risposte diverse. Se ne danno due o una, `--as-of` non
     naviga la catena e il banco lo dice.
  ② la struttura nel database dev'essere una CATENA (A->B->C) e non due ritiri paralleli
     (A->C, B->C): sono strutture diverse e cambiano la domanda.

RISULTATO (28/08 20:52):

  struttura verificata nel db:  8bd8e9e922e2 -> 354f8b6cbab5 -> 2db7a60f3c0b -> VIVO
                                 (4141)          (5252)          (6363)
  => e' una catena vera, non ritiri paralleli. Controllo ② superato.

  --as-of dopo-A -> «Il magazzino M-55 contiene **4141** pezzi.»
                      con annotato retired: 5252
  --as-of dopo-B -> «Il magazzino M-55 contiene **5252** pezzi.»
                      con annotato retired: 4141
  --as-of dopo-C -> «Il magazzino M-55 contiene **6363** pezzi.»
                      con annotati retired: 4141 e 5252
  => TRE istanti, TRE risposte diverse. Controllo ① superato: `--as-of` naviga la catena.

DETTAGLIO CHE VALE LA PENA NOTARE: l'annotazione «trattenuto (retired)» non elenca «cio'
che era gia' stato ritirato a quell'istante» ma **gli altri anelli della catena** — a
dopo-A annota 5252, che a quell'istante non esisteva ancora. E' coerente (dice cosa quel
fatto e' diventato) e informativo, ma **non e' una fotografia del passato**: chi lo
legge come tale sbaglia epoca.

REGIME: store temporaneo isolato via `HIPPO_DATA_DIR` (⚠️ `ENGRAM_DATA_DIR` non isola),
FUORI da pytest, un processo per le scritture e la CLI per le letture, porta CLI.
Corpus di Aurelio intatto e mai toccato. ⚠️ `--as-of` vuole un **Unix epoch**.

⚠️ LIMITE: tre anelli, un topic, una porta. Non dice nulla su catene molto piu' lunghe
ne' sui ritiri prodotti da `heal_contradictions`, che restano non provati con `--as-of`.

RIPRODUCI:  python docs/stato-reale/banchi/ws6-le-catene-lunghe-e-il-viaggio-nel-tempo.py
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path


def main() -> None:
    from verimem.client import Memory
    from verimem.config import CONFIG
    db = Path(CONFIG.semantic_db)
    print(f"store: {db}")
    mem = Memory(str(db))
    marks = []
    for v in ("4141", "5252", "6363"):
        mem.add(f"Il magazzino M-55 contiene {v} pezzi.", topic="cat/uno",
                source=f"M-55: {v} pezzi.")
        time.sleep(2)
        marks.append(int(time.time()))
        time.sleep(1)
    for et, ts in zip(("dopo-A", "dopo-B", "dopo-C"), marks):
        print(f"\n### --as-of {et} ({ts}) — output integrale, non filtrato ###")
        out = subprocess.run([sys.executable, "-m", "verimem.cli", "recall",
                              "magazzino M-55", "--as-of", str(ts)],
                             capture_output=True, text=True)
        for riga in (out.stdout + out.stderr).splitlines():
            if riga.startswith("20") or "RuntimeWarning" in riga:
                continue
            print(f"  {riga}")


if __name__ == "__main__":
    main()
