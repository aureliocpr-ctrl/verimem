"""Quali dei numeri che ho pubblicato stanotte sono ancora veri?

@ws7 (06:34) misura la stessa cosa sui suoi aggregati: tre su cinque invecchiati
in due ore, e i due che reggono sono quelli che RILEGGE DA UNO SCRIPT. Faccio la
stessa domanda ai miei, prima che li legga Aurelio.

Regola che ne esce, e che questo banco applica a se stesso: un numero che si
rilegge non invecchia; uno scritto a mano nel documento sì.

Ogni riga: il numero PUBBLICATO, quello di ADESSO, e il verdetto.
SOLA LETTURA.
"""
import datetime
import json
import os
import sqlite3

DB = os.path.expanduser(os.path.join("~", ".engram", "semantic", "semantic.db"))
FLOOR = DB + ".floor.json"
ORA = datetime.datetime.now()
con = sqlite3.connect("file:%s?mode=ro" % DB.replace(os.sep, "/"), uri=True)


def riga(doc, cosa, pubblicato, adesso, stabile=None):
    if stabile is None:
        stabile = str(pubblicato) == str(adesso)
    print("%-6s %-42s %14s %14s   %s"
          % (doc, cosa[:42], pubblicato, adesso,
             "REGGE" if stabile else "SCADUTO"))


print("%-6s %-42s %14s %14s   %s"
      % ("doc", "il numero", "PUBBLICATO", "ADESSO", "verdetto"))

# --- il pavimento persistito: si rilegge dal file
try:
    d = json.load(open(FLOOR, encoding="utf-8"))
    riga("60", "floor persistito", "0.8781", "%s" % d.get("floor"))
    riga("60", "n_facts nel file", "14485", "%s" % d.get("n_facts"))
except Exception as e:                      # noqa: BLE001
    print("floor.json non leggibile: %s" % e)

# --- il margine: si ricalcola
vivi = con.execute(
    "SELECT COUNT(*) FROM facts WHERE superseded_by IS NULL").fetchone()[0]
salvato = int(d.get("n_facts") or 0)
margine = int(max(1, salvato) * 0.05 - abs(vivi - salvato))
riga("53", "margine prima del ricalcolo", "105", str(margine), stabile=False)

# --- la perdita del corpus
scritti = con.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
quar = con.execute(
    "SELECT COUNT(*) FROM facts WHERE superseded_by IS NULL "
    "AND status='quarantined'").fetchone()[0]
serviti = vivi - quar
riga("59", "fatti scritti", "16755", str(scritti))
riga("59", "davvero serviti", "13187", str(serviti))
riga("59", "perdita %", "21", "%d" % round(100.0 * (scritti - serviti) / scritti))

# --- i quarantinati muti
muti = con.execute(
    "SELECT COUNT(*) FROM facts WHERE status='quarantined' "
    "AND superseded_by IS NULL AND quarantined_by IS NULL").fetchone()[0]
riga("59", "quarantinati senza layer", "661", str(muti))

# --- il registro di undo e i candidati
undo = con.execute(
    "SELECT COUNT(*) FROM facts_undo_log WHERE op_type='supersede'").fetchone()[0]
riga("64", "voci di supersessione nel registro", "336", str(undo))

# --- le contraddizioni
contr = con.execute(
    "SELECT COUNT(*) FROM contradictions WHERE resolved_at IS NULL").fetchone()[0]
riga("63", "contraddizioni irrisolte", "93263", str(contr))

con.close()
print()
print("I numeri che REGGONO sono quelli che descrivono un file o un evento")
print("(il floor persistito, la transizione delle 02:52:23). Quelli che")
print("SCADONO contano righe di un corpus che cresce mentre lo guardi.")
print("⇒ nel documento vanno scritti con l'istante, e chi li cita li rilegge.")
