"""Quanto e' larga la classe «stessa domanda, entita' diversa»?

Una cella sola (Ancona -> Bologna) e' un aneddoto. Qui si scambia l'entita' di
CINQUE TIPI diversi sulla stessa domanda, e si tiene accanto la popolazione che
gia' funziona (attributo assente), perche' un confine si vede solo con
tutti e due i lati.

  A  ATTRIBUTO ASSENTE   nessun fatto ci si avvicina        -> deve astenersi
  B  ENTITA' SCAMBIATA   stessa domanda, altro soggetto     -> deve astenersi
                         (citta', persona, codice, numero di serie, anno)

Il verdetto si legge dal campo `abstained`, e si stampa ANCHE il fatto
restituito: «non si astiene» e «restituisce la cosa sbagliata» sono due
affermazioni diverse e servono entrambe.
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import tempfile
import threading

PY = str(pathlib.Path(sys.argv[1]) / "Scripts" / "python.exe")
CASA = pathlib.Path(tempfile.mkdtemp(prefix="quanto_largo_"))
AMB = {k: v for k, v in os.environ.items()
       if not k.startswith(("HIPPO_", "ENGRAM_", "VERIMEM_"))}
AMB.update(HIPPO_DATA_DIR=str(CASA / "dati"), PYTHONUNBUFFERED="1")

SORG = ("Verbale del collaudo del 12 marzo 2024: il ripetitore di Ancona ha "
        "inoltrato 4200 messaggi, il tecnico Rossi era di turno, il magazzino "
        "K-77 misura 2600 metri quadrati e l'apparato con matricola SN-1180 ha "
        "superato la prova.")
SCRITTI = [
    ("Il ripetitore di Ancona ha inoltrato 4200 messaggi.", "c/citta"),
    ("Il tecnico Rossi era di turno al collaudo.", "c/persona"),
    ("Il magazzino K-77 misura 2600 metri quadrati.", "c/codice"),
    ("L'apparato con matricola SN-1180 ha superato la prova.", "c/matricola"),
    ("Il collaudo si e' svolto il 12 marzo 2024.", "c/anno"),
]
DOMANDE = [
    ("A attributo  colore del ripetitore", "di che colore e' il ripetitore di Ancona"),
    ("A attributo  stipendio di Rossi", "che stipendio ha il tecnico Rossi"),
    ("A attributo  proprietario del magazzino", "chi e' il proprietario del magazzino K-77"),
    ("B citta'     Bologna al posto di Ancona", "quanti messaggi ha inoltrato il ripetitore di Bologna"),
    ("B persona    Ferrari al posto di Rossi", "il tecnico Ferrari era di turno al collaudo"),
    ("B codice     K-88 al posto di K-77", "quanti metri quadrati misura il magazzino K-88"),
    ("B matricola  SN-9990 al posto di SN-1180", "l'apparato con matricola SN-9990 ha superato la prova"),
    ("B anno       2019 al posto di 2024", "cosa e' successo al collaudo del 12 marzo 2019"),
]

frame = [{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
    "protocolVersion": "2024-11-05", "capabilities": {},
    "clientInfo": {"name": "banco", "version": "1"}}},
    {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}]
i = 2
for prop, topic in SCRITTI:
    frame.append({"jsonrpc": "2.0", "id": i, "method": "tools/call", "params": {
        "name": "hippo_remember",
        "arguments": {"proposition": prop, "topic": topic, "source": SORG}}}); i += 1
mappa = {}
for nome, q in DOMANDE:
    frame.append({"jsonrpc": "2.0", "id": i, "method": "tools/call", "params": {
        "name": "hippo_trust_report", "arguments": {"query": q}}})
    mappa[i] = nome; i += 1
ATTESE = i - 1

p = subprocess.Popen([PY, "-u", "-m", "verimem.mcp_server"], stdin=subprocess.PIPE,
                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                     env=AMB, bufsize=1)
risp, fine = {}, threading.Event()


def leggi():
    for riga in p.stdout:
        try:
            o = json.loads(riga)
        except Exception:
            continue
        if isinstance(o, dict) and "id" in o:
            risp[o["id"]] = o
            if len(risp) >= ATTESE:
                fine.set(); return


#: ⚠️ DRENARE stderr, o il server si BLOCCA. La prima forma di questo banco ha
#: ricevuto 3 risposte su 14 e si e' piantata: `stderr=PIPE` mai letto, structlog
#: riempie il buffer del sistema (~64 KB) e il processo figlio si ferma a
#: scrivere. Con poche chiamate non si vede; a tredici si vede. Non e' un
#: difetto del prodotto: e' la disciplina di chi apre una pipe.
def _drena():
    for _ in p.stderr:
        pass


threading.Thread(target=_drena, daemon=True).start()
threading.Thread(target=leggi, daemon=True).start()
p.stdin.write("".join(json.dumps(f) + "\n" for f in frame)); p.stdin.flush()
fine.wait(timeout=300)
print(f"  risposte {len(risp)}/{ATTESE}   (tutte queste domande devono ASTENERSI)\n")

conta = {"A": [0, 0], "B": [0, 0]}
for k, nome in sorted(mappa.items()):
    o = risp.get(k)
    if not o:
        print(f"  ⚠️ {nome}: nessuna risposta"); continue
    d = json.loads(o["result"]["content"][0]["text"])
    ast = bool(d.get("abstained"))
    gruppo = nome[0]
    conta[gruppo][0 if ast else 1] += 1
    reso = ""
    for f in (d.get("facts") or [])[:1]:
        reso = f"  -> «{str(f.get('proposition'))[:52]}»"
    print(f"  {'✅' if ast else '🔴'} {nome:<38} abstained={str(ast):<5} "
          f"n_facts={d.get('n_facts')}{reso}")
print(f"\n  A attributo assente : {conta['A'][0]} si astiene · {conta['A'][1]} NO")
print(f"  B entita' scambiata : {conta['B'][0]} si astiene · {conta['B'][1]} NO")
try:
    p.stdin.close(); p.wait(timeout=15)
except Exception:
    p.kill()
