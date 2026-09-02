"""`verimem import` con un export VERO: mantiene la promessa «consent-first»?

Nella passata delle 15:25 questo comando l'avevo provato con un file INESISTENTE
(rc=1, «file not found») e l'avevo contato fra i miei errori, non fra le prove.
E' un buco dichiarato nel mio referto, e il README lo mostra in vetrina:

    verimem import conversations.json       # list a ChatGPT/Claude export
                                            # (imports nothing without flags)
    verimem import conversations.json --project verimem --since 2026-06-01 --all-matching

DUE PROMESSE DA SEPARARE:
  1. senza flag ELENCA e non importa   -> il corpus deve restare a ZERO fatti
  2. con i flag importa                -> qui NON lo eseguo: scriverebbe davvero,
                                          e il punto della prova 1 e' che non scriva

REGIME: venv col wheel, data dir NUOVA, env ripulito per enumerazione del prefisso.
"""
from __future__ import annotations

import json
import os
import pathlib
import sqlite3
import subprocess
import sys
import tempfile

EXE = str(pathlib.Path(sys.argv[1]) / "Scripts" / "verimem.exe")
CASA = pathlib.Path(tempfile.mkdtemp(prefix="prova_import_"))
AMB = {k: v for k, v in os.environ.items()
       if not k.startswith(("HIPPO_", "ENGRAM_", "VERIMEM_"))}
AMB["HIPPO_DATA_DIR"] = str(CASA / "dati")

#: la forma di un export ChatGPT: lista di conversazioni con `mapping`
EXPORT = [{
    "title": "Collaudo di Ancona",
    "create_time": 1780000000.0,
    "mapping": {
        "n1": {"id": "n1", "message": {"author": {"role": "user"}, "create_time": 1780000000.0,
                                       "content": {"content_type": "text", "parts": [
                                           "Quanti messaggi ha inoltrato il ripetitore di Ancona?"]}},
               "parent": None, "children": ["n2"]},
        "n2": {"id": "n2", "message": {"author": {"role": "assistant"}, "create_time": 1780000001.0,
                                       "content": {"content_type": "text", "parts": [
                                           "Ne ha inoltrati 4200, secondo il verbale del 12 marzo."]}},
               "parent": "n1", "children": []},
    }}]
F = CASA / "conversations.json"
F.write_text(json.dumps(EXPORT, ensure_ascii=False), encoding="utf-8")


def fatti() -> int:
    db = next(iter((CASA / "dati").rglob("semantic.db")), None)
    if not db:
        return 0
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        return c.execute("SELECT count(*) FROM facts").fetchone()[0]
    finally:
        c.close()


print(f"  export: {F}  ({F.stat().st_size} byte, 1 conversazione, 2 messaggi)")
p = subprocess.run([EXE, "import", str(F)], capture_output=True, text=True,
                   env=AMB, cwd=str(CASA), timeout=300)
tutto = (p.stdout or "") + (p.stderr or "")
print(f"  rc={p.returncode}")
for r in [x for x in tutto.splitlines() if x.strip()][:12]:
    print(f"    {r[:110]}")
n = fatti()
print(f"\n  fatti nel corpus DOPO l'import senza flag: {n}")
print(f"  {'✅ la promessa REGGE: elenca e non importa' if n == 0 else '🔴 ha scritto ' + str(n) + ' fatti senza che glielo chiedessi'}")
