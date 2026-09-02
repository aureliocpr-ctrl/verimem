"""`verimem facts undo <op_id>`: «reverse a retirement — the lost fact comes back».

E' il percorso di RECUPERO, e per un rilascio conta piu' di una funzione nuova:
e' cio' che un utente cerca quando la memoria gli ha mangiato qualcosa.

Il banco in quattro passi, e ognuno con il suo controllo:
  1. scrivo A                          -> deve essere nel corpus
  2. scrivo B che aggiorna A           -> A deve risultare superseduto
  3. leggo `facts retirement-log`      -> deve dare un op_id (senza, la promessa
                                          non e' nemmeno raggiungibile)
  4. `facts undo <op_id>`              -> A deve TORNARE

⚠️ Il controllo del passo 2 non e' decorativo: se la supersessione non avviene,
il passo 4 non ha niente da annullare e il banco direbbe «promessa mantenuta»
misurando il nulla. E' la trappola in cui sono caduta cinque volte oggi.
"""
from __future__ import annotations

import os
import pathlib
import re
import sqlite3
import subprocess
import sys
import tempfile

EXE = str(pathlib.Path(sys.argv[1]) / "Scripts" / "verimem.exe")
CASA = pathlib.Path(tempfile.mkdtemp(prefix="prova_undo_"))
AMB = {k: v for k, v in os.environ.items()
       if not k.startswith(("HIPPO_", "ENGRAM_", "VERIMEM_"))}
AMB["HIPPO_DATA_DIR"] = str(CASA / "dati")

SORG_A = "Rilevazione delle 09:00: il contatore del reparto nord segna 318 pezzi."
SORG_B = "Rilevazione delle 17:00: il contatore del reparto nord segna 412 pezzi."
A = "Il contatore del reparto nord segna 318 pezzi."
B = "Il contatore del reparto nord segna 412 pezzi."


def sh(*a):
    p = subprocess.run([EXE, *a], capture_output=True, text=True,
                       env=AMB, cwd=str(CASA), timeout=300)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def stato_di(frammento: str):
    db = next(iter((CASA / "dati").rglob("semantic.db")), None)
    if not db:
        return None
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        for prop, st, sup in c.execute(
                "SELECT proposition, status, superseded_by FROM facts"):
            if frammento in (prop or ""):
                return (st, "SUPERSEDUTO" if sup else "vivo")
    finally:
        c.close()
    return None


rc, _ = sh("save", A, "--topic", "recupero/contatore", "--source", SORG_A)
print(f"  1. scritto A   rc={rc}   stato: {stato_di('318')}")
rc, _ = sh("save", B, "--topic", "recupero/contatore", "--source", SORG_B)
print(f"  2. scritto B   rc={rc}   A ora: {stato_di('318')}   B: {stato_di('412')}")

#: ⛔ `COLUMNS=200` NON È UN DETTAGLIO: senza, Rich tronca le colonne dentro la
#: pipe e l'`op_id` esce a metà. È metà della cura descritta sotto.
AMB["COLUMNS"] = "200"
rc, out = sh("facts", "retirement-log")
righe = [r for r in out.splitlines() if r.strip()][:6]
print(f"  3. retirement-log rc={rc}")
for r in righe:
    print(f"       {r[:104]}")
#: ⛔ IL DIFETTO CHE QUESTO BANCO AVEVA, e che mi ha ingannata DUE volte — il
#: 22/08 e di nuovo il 24/08 sul wheel 0.7.6, dove per un minuto ho creduto a
#: una regressione del prodotto. Cercare la PRIMA stringa esadecimale pesca il
#: `fact_id` del PERDENTE, non l'`op_id` della colonna `undo`; e la pipe stretta
#: lo tronca a 9 caratteri, così `facts undo` risponde `not found` e sembra
#: rotto il prodotto. NON lo è: con l'op_id giusto ripristina, misurato due
#: volte («restored: fact_id=…», ed entrambi i fatti VIVO nel db).
#: ✅ La cura è doppia e serve tutta: `COLUMNS=200` sopra, e qui l'op_id è
#: esattamente 16 esadecimali e sta in FONDO alla riga — si prende l'ULTIMO.
m = re.search(r"\b([0-9a-f]{16})\b(?!.*\b[0-9a-f]{16}\b)", out, re.S)
if not m:
    print("\n  ⚠️ nessun op_id nel log: il passo 4 non e' raggiungibile da qui.")
    print("     NON concludo che `undo` sia rotto — concludo che con QUESTO")
    print("     percorso l'utente non arriva all'identificatore che gli serve.")
    sys.exit(0)
op = m.group(1)
rc, out = sh("facts", "undo", op)
print(f"\n  4. facts undo {op}   rc={rc}")
for r in [x for x in out.splitlines() if x.strip()][:4]:
    print(f"       {r[:104]}")
dopo = stato_di("318")
print(f"\n  A dopo l'undo: {dopo}")
print(f"  {'✅ IL FATTO E TORNATO' if dopo and dopo[1] == 'vivo' else '🔴 A e ancora ' + str(dopo)}")
