"""Quando ammette senza giudizio, il prodotto lo DICHIARA o tace?

E' la domanda che separa un degrado onesto da un'affermazione falsa, ed e' il
criterio di Aurelio: «nessun analista deve poter dire che afferma cose che non fa».

Un claim che la sua fonte SMENTISCE, scritto sulla porta MCP col ramo daemon
non disponibile (`ENGRAM_ENCODE_SERVICE=0` -> `_gate_via_daemon` esce subito,
lo STESSO ramo della finestra di ~20 s di un utente nuovo).

Si guardano TRE cose, perche' «lo dice» puo' voler dire tre cose diverse:
  1. la RISPOSTA alla scrittura   -> c'e' un grounding_score? e' null? c'e' un avviso?
  2. il FATTO nello store         -> che status ha? che grounding_score?
  3. la RILETTURA                 -> tornando indietro, l'utente vede che non fu giudicato?

⚠️ stdin resta APERTO fino all'ultima risposta.
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sqlite3
import sys
import tempfile
import threading
import time

PY = str(pathlib.Path(sys.argv[1]) / "Scripts" / "python.exe")
CASA = pathlib.Path(tempfile.mkdtemp(prefix="lo_dice_"))
AMB = {k: v for k, v in os.environ.items()
       if not k.startswith(("HIPPO_", "ENGRAM_", "VERIMEM_"))}
AMB.update(HIPPO_DATA_DIR=str(CASA / "dati"), PYTHONUNBUFFERED="1",
           ENGRAM_ENCODE_SERVICE="0")

SORGENTE = ("Verbale del turno di notte: il contatore del reparto nord ha "
            "registrato 318 pezzi, controfirmato dal capoturno Bianchi.")
FALSO = "Il reparto nord ha registrato 999 pezzi."
frame = [
    {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
        "protocolVersion": "2024-11-05", "capabilities": {},
        "clientInfo": {"name": "utente-nuovo", "version": "1.0"}}},
    {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
    {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {
        "name": "hippo_remember",
        "arguments": {"proposition": FALSO, "topic": "collaudo/falso",
                      "source": SORGENTE}}},
    {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {
        "name": "hippo_recall",
        "arguments": {"query": "quanti pezzi ha registrato il reparto nord", "k": 3}}},
]
p = subprocess.Popen([PY, "-u", "-m", "verimem.mcp_server"],
                     stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE, text=True, env=AMB, bufsize=1)
risp: dict[int, str] = {}
fine = threading.Event()


def leggi():
    for riga in p.stdout:
        try:
            o = json.loads(riga)
        except Exception:
            continue
        if isinstance(o, dict) and "id" in o:
            risp[o["id"]] = riga
            if len(risp) >= 3:
                fine.set(); return


threading.Thread(target=leggi, daemon=True).start()
p.stdin.write("".join(json.dumps(f) + "\n" for f in frame))
p.stdin.flush()
fine.wait(timeout=240)

print("  ── ① LA RISPOSTA ALLA SCRITTURA ──")
print("  " + (risp.get(2, "(nessuna)")[:900]))
print("\n  ── ③ LA RILETTURA: l'utente ritrova il fatto falso? ──")
r3 = risp.get(3, "")
print(f"  il claim falso torna dalla recall: {'SI' if '999' in r3 else 'no'}")
print("  " + r3[:500])
try:
    p.stdin.close(); p.wait(timeout=20)
except Exception:
    p.kill()

print("\n  ── ② IL FATTO NELLO STORE ──")
db = next(iter((CASA / "dati").rglob("semantic.db")), None)
if db:
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    cols = [r[1] for r in c.execute("PRAGMA table_info(facts)")]
    interessanti = [x for x in ("proposition", "status", "grounding_score",
                                "grounding_span", "quarantined_by") if x in cols]
    for riga in c.execute(f"SELECT {','.join(interessanti)} FROM facts"):
        for k, v in zip(interessanti, riga):
            print(f"    {k:<18} {str(v)[:70]}")
