"""La stessa scrittura, con e senza la variabile che la CLI non imposta.

`local_grounding.py:658` fa passare dal daemon caldo SOLO se `_delegate_only()`,
cioe' se `HIPPO_ENCODE_DELEGATE_ONLY=1`. `mcp_server.py:14921` la imposta da se'
con `setdefault`; la CLI **no**. Chi installa e lancia `verimem save` non ce l'ha.

A  senza la variabile  = quello che ha chi installa e usa la CLI
B  con  la variabile   = quello che ha l'MCP server, e che abbiamo noi in
                         `.claude.json` (per questo nessuna di noi l'ha mai vista)

PREDIZIONE: A ~16 s, B pochi secondi, **entrambe judged=True**. Se B fosse
`judged=False` la variabile non farebbe risparmiare tempo: farebbe SALTARE il
giudizio, e sarebbe un difetto molto peggiore di una promessa sbagliata.
Se A e B fossero uguali la mia lettura del ramo e' falsa.
"""
from __future__ import annotations

import os
import pathlib
import subprocess
import sys
import tempfile
import time

EXE = str(pathlib.Path(sys.argv[1]) / "Scripts" / "verimem.exe")
SORG = ("Verbale del turno di notte: il contatore del reparto nord ha registrato "
        "{n} pezzi, controfirmato dal capoturno Bianchi.")


def giro(nome: str, extra: dict[str, str], base: int):
    casa = pathlib.Path(tempfile.mkdtemp(prefix="delegate_"))
    amb = {k: v for k, v in os.environ.items()
           if not k.startswith(("HIPPO_", "ENGRAM_", "VERIMEM_"))}
    amb["HIPPO_DATA_DIR"] = str(casa / "dati")
    amb.update(extra)
    for i in range(2):
        t0 = time.time()
        p = subprocess.run(
            [EXE, "remember", f"Il reparto nord ha registrato {base+i} pezzi.",
             "--topic", f"del/g{i}", "--source", SORG.format(n=base+i)],
            capture_output=True, text=True, env=amb, cwd=str(casa), timeout=300)
        tutto = (p.stdout or "") + (p.stderr or "")
        giud = "judged=True" in tutto
        punteggio = ""
        for pezzo in tutto.split():
            if pezzo.startswith("grounding_score="):
                punteggio = pezzo.split("=", 1)[1][:6]
        print(f"  {nome:<38} giro {i+1}  {time.time()-t0:6.2f}s  "
              f"judged={'True ' if giud else 'FALSE'}  score={punteggio or '(assente)'}")


giro("A  senza  (chi installa, via CLI)", {}, 700)
giro("B  con DELEGATE_ONLY=1 (MCP, noi)", {"HIPPO_ENCODE_DELEGATE_ONLY": "1"}, 800)
