"""Quanto manca prima che il pavimento salvato venga ricalcolato.

client.py serve il valore persistito finche' il conteggio dei fatti VIVI non
deriva oltre _FLOOR_DRIFT dal conteggio scritto nel file. Il contratto di
count() dice "Live facts only (superseded excluded)": e' quello il conteggio
che decide, non il totale dei fatti.

⚠️ LEZIONE PAGATA (31/08 ore 02:52): la prima versione di questo banco aveva
n_facts SCRITTO A MANO (13795). Quando il prodotto ha ricalcolato e il file e'
passato a 14485, il banco ha continuato a confrontare col vecchio valore e
diceva "RICALCOLA, margine -4" su uno store appena ricalibrato. Un banco che
mente e' peggio di nessun banco - e nel documento avevo scritto io che il
numero "si rilegge, non si ricopia".
Adesso legge n_facts DAL FILE a ogni esecuzione.

SOLA LETTURA: nessuna scrittura, nessun rm.
"""
import json
import os
import sqlite3
import time

from verimem.client import Memory

DB = os.path.expanduser(os.path.join("~", ".engram", "semantic", "semantic.db"))
FLOOR = DB + ".floor.json"

try:
    with open(FLOOR, encoding="utf-8") as fh:
        persistito = json.load(fh)
    quando = time.strftime("%Y-%m-%d %H:%M:%S",
                           time.localtime(os.path.getmtime(FLOOR)))
except Exception as e:                      # noqa: BLE001 - il file puo' mancare
    persistito, quando = {}, None
    print("floor.json non leggibile (%s): senza file il prodotto ricalcola" % e)

salvato = int(persistito.get("n_facts") or 0)
valore = persistito.get("floor")
drift = Memory._FLOOR_DRIFT
soglia = max(1, salvato) * drift

con = sqlite3.connect("file:%s?mode=ro" % DB.replace(os.sep, "/"), uri=True)
tot = con.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
vivi = con.execute(
    "SELECT COUNT(*) FROM facts WHERE superseded_by IS NULL").fetchone()[0]
con.close()

print("floor.json     : floor=%s  n_facts=%s   mtime %s"
      % (valore, salvato, quando))
print("_FLOOR_DRIFT   : %s  =>  tolleranza %.1f fatti" % (drift, soglia))
for nome, n in (("facts TOTALI", tot), ("facts VIVI", vivi)):
    d = abs(n - salvato)
    esito = "USA IL SALVATO" if d <= soglia else "RICALCOLA"
    print("%-14s = %6d   scarto dal salvato(%d) = %+5d   %s   margine %+.0f"
          % (nome, n, salvato, n - salvato, esito, soglia - d))
print("\nil conteggio che DECIDE e' quello dei VIVI: count() dichiara "
      "\"Live facts only (superseded excluded)\".")
