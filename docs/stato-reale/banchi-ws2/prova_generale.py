"""La prova generale del gate (d): le promesse del README, eseguite DA UTENTE.

Ogni riga qui sotto e' un comando che il README di verimem MOSTRA a chi installa.
Non e' una parafrasi: sono estratte dai blocchi ```bash del README con awk.

REGIME (dichiarato, perche' il regime decide il verdetto):
  · venv separato, verimem installato da wheel — NON il repo
  · HIPPO_DATA_DIR su una cartella NUOVA e vuota: e' il primo avvio di un utente
  · si esegue dalla cartella del venv, NON dal repo: chi installa non ha il repo
  ⚠️ NON isolato: la cache dei modelli HuggingFace e' dell'utente, non del venv,
     quindi il giudice CE QUI C'E'. Il caso «CE assente» e' di @ws5 e non e' questo.

ESCLUSI di proposito, e il perche':
  · `verimem console`      aprirebbe il browser mentre Aurelio gioca
  · `verimem gateway serve` lascerebbe un processo in ascolto (regola: chiudi
                            cio' che apri, e uccidere si fa a DUE gambe)
  · `verimem airgap --live` idem, apre socket

Il verdetto di ogni riga e' `rc` + la prima riga utile. Un rc!=0 NON e' per forza
un difetto (un comando puo' rifiutare a ragione) — la colonna serve a decidere
DOVE guardare, non a contare i rossi.
"""
from __future__ import annotations

import os
import pathlib
import subprocess
import sys
import tempfile

VENV = sys.argv[1]
EXE = str(pathlib.Path(VENV) / "Scripts" / "verimem.exe")
CASA = pathlib.Path(tempfile.mkdtemp(prefix="utente_nuovo_"))
DATI = CASA / "dati"
AMB = dict(os.environ, HIPPO_DATA_DIR=str(DATI))
for k in ("ENGRAM_DATA_DIR", "HIPPO_OFFLINE", "HIPPO_ENCODE_DELEGATE_ONLY"):
    AMB.pop(k, None)

#: un documento vero per i comandi che ne vogliono uno
DOC = CASA / "contratto.txt"
DOC.write_text(
    "CLAUSOLA DI RECESSO. Il conduttore puo' recedere con preavviso di sei mesi.\n"
    "Il canone e' di 900 euro al mese e si rivaluta ogni dodici mesi.\n"
    "TERMINATION CLAUSE. Either party may terminate with six months notice.\n",
    encoding="utf-8")

PROMESSE = [
    ("--help",                    [EXE, "--help"]),
    ("save + asserted-at",        [EXE, "save", "The rent is 900/month.",
                                   "--asserted-at", "2026-03-15"]),
    ("trust + verified-by",       [EXE, "trust", "the deploy is green",
                                   "--verified-by", "ci:main:green"]),
    ("facts retirement-log",      [EXE, "facts", "retirement-log"]),
    ("facts retirement-log -c",   [EXE, "facts", "retirement-log", "--counts"]),
    ("index <file>",              [EXE, "index", str(DOC)]),
    ("search-docs",               [EXE, "search-docs", "termination clause"]),
    ("airgap (solo config)",      [EXE, "airgap"]),
    ("gateway keys create",       [EXE, "gateway", "keys", "create",
                                   "--tenant", "acme", "--name", "laptop"]),
    ("gateway backup",            [EXE, "gateway", "backup", str(CASA / "snap")]),
    ("import <export>",           [EXE, "import", str(CASA / "conversations.json")]),
]

print(f"  casa dell'utente nuovo: {CASA}")
print(f"  eseguibile: {EXE}\n")
for nome, cmd in PROMESSE:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, env=AMB,
                           cwd=str(CASA), timeout=180)
        uscita = (p.stdout or "").strip().splitlines()
        errore = (p.stderr or "").strip().splitlines()
        prima = next((r for r in uscita if r.strip()), "")
        if not prima:
            prima = next((r for r in errore if r.strip()), "(nessuna uscita)")
        print(f"  rc={p.returncode:<3} {nome:<26} | {prima[:110]}")
        if p.returncode != 0 and errore:
            coda = [r for r in errore if r.strip()][-1]
            if coda[:110] != prima[:110]:
                print(f"  {'':<30} \_ ultima riga stderr: {coda[:110]}")
    except subprocess.TimeoutExpired:
        print(f"  rc=TMO {nome:<26} | 180 s senza uscire")
