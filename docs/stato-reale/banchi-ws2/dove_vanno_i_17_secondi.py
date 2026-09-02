"""I 17 secondi di `remember` sono il moat, o il comando?

`cli.py:1155` promette «Store one fact through the full moat — the 2-second
quickstart» e misurati sono 17,8 / 16,8 / 16,9 s: stabile, quindi non e' il
caricamento a freddo. La domanda che decide il referto e' QUALE meta' costa,
perche' «il comando e' lento» e «il moat costa 15 s e l'aiuto promette 2» si
curano in due modi opposti.

A  con --source     il moat entailment GIRA (e' cio' che «full moat» promette)
B  senza --source   niente da giudicare: il moat NON gira (documentato dal
                    server MCP: «WITHOUT a source ... the moat does not run»)
C  --help           il pavimento: avvio del processo e nient'altro

PREDIZIONE: se A-B ~ 15 s, il costo e' il giudice e la promessa dei 2 secondi e'
scritta sul comando sbagliato. Se A ~ B, il giudice non c'entra e il lento e' il
comando — e allora la mia lettura e' falsa.
"""
from __future__ import annotations

import os
import pathlib
import subprocess
import sys
import tempfile
import time

EXE = str(pathlib.Path(sys.argv[1]) / "Scripts" / "verimem.exe")
CASA = pathlib.Path(tempfile.mkdtemp(prefix="dove_vanno_"))
AMB = {k: v for k, v in os.environ.items()
       if not k.startswith(("HIPPO_", "ENGRAM_", "VERIMEM_"))}
AMB["HIPPO_DATA_DIR"] = str(CASA / "dati")
SORG = ("Verbale del turno di notte: il contatore del reparto nord ha registrato "
        "{n} pezzi, controfirmato dal capoturno Bianchi.")


def crono(a):
    t0 = time.time()
    p = subprocess.run([EXE, *a], capture_output=True, text=True,
                       env=AMB, cwd=str(CASA), timeout=300)
    tutto = (p.stdout or "") + (p.stderr or "")
    #: il giudizio e' passato? il campo lo dice, e leggerlo evita di dedurlo
    giudicato = "grounding_score" in tutto and "grounding_score=None" not in tutto
    return p.returncode, time.time() - t0, giudicato


def media(nome, fai, giri=3):
    esiti = [fai(i) for i in range(giri)]
    t = [e[1] for e in esiti]
    g = sum(1 for e in esiti if e[2])
    print(f"  {nome:<30} {min(t):5.2f}-{max(t):5.2f}s  media {sum(t)/len(t):5.2f}s"
          f"   giudicati {g}/{giri}")
    return sum(t) / len(t)


c = media("C  --help (pavimento)",
          lambda i: crono(["--help"]))
b = media("B  remember SENZA --source",
          lambda i: crono(["remember", f"Il reparto nord ha registrato {400+i} pezzi.",
                           "--topic", f"senza/g{i}"]))
a = media("A  remember CON --source",
          lambda i: crono(["remember", f"Il reparto nord ha registrato {500+i} pezzi.",
                           "--topic", f"con/g{i}", "--source", SORG.format(n=500+i)]))
print(f"\n  il moat costa   A-B = {a-b:5.2f}s      il resto del comando   B-C = {b-c:5.2f}s")
print(f"  la promessa dell'--help e' 2 s: {'il moat e la causa' if a-b > 8 else 'NON e il moat: la mia lettura cade'}")
