"""Che cosa sta per uscire dalla finestra di recupero, e quanto vale.

Un ritiro si annulla per SETTE GIORNI: dopo, il fatto resta ritirato per sempre.
`verimem doctor` dice quanti sono reversibili adesso, ma non QUANDO scadono ne'
QUANTI valga la pena recuperare.

Due numeri che il doc 41 rende calcolabili:
  - i ritiri SBAGLIATI (i due testi parlano d'altro) sono il 10,2% dopo il
    25/08 e il 32,7% prima;
  - quindi la finestra contiene una quota stimabile di fatti VERI che stanno
    per diventare irrecuperabili.

⚠️ La stima non dice QUALI: dice quanti. Per sapere quali bisogna leggerli, e
il restore richiede mandato - qui si MISURA soltanto.

SOLA LETTURA sullo store.
"""
import datetime
import os
import sqlite3

DB = os.path.expanduser(os.path.join("~", ".engram", "semantic", "semantic.db"))
ORA = datetime.datetime.now()

con = sqlite3.connect("file:%s?mode=ro" % DB.replace(os.sep, "/"), uri=True)

# PRESIDIO: che cosa c'e' nella tabella, prima di contare.
tab = [r[0] for r in con.execute(
    "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%undo%'")]
print("tabelle di undo:", tab)
if not tab:
    print("nessuna tabella di undo: mi fermo")
    raise SystemExit(0)

T = tab[0]
cols = [r[1] for r in con.execute("PRAGMA table_info(%s)" % T)]
print("colonne:", cols)
tot = con.execute("SELECT COUNT(*) FROM %s" % T).fetchone()[0]
print("righe totali: %d" % tot)

campo_t = next((c for c in ("created_at", "ts", "at", "when_ts") if c in cols), None)
campo_k = next((c for c in ("kind", "op", "operation") if c in cols), None)
if not campo_t:
    print("nessuna colonna temporale riconosciuta: mi fermo")
    raise SystemExit(0)

righe = con.execute("SELECT %s%s FROM %s"
                    % (campo_t, (", " + campo_k) if campo_k else "", T)).fetchall()
con.close()

FINESTRA = 7 * 86400
vive, scadute = [], 0
for r in righe:
    try:
        t = float(r[0])
    except Exception:      # noqa: BLE001 - potrebbe essere una stringa ISO
        try:
            t = datetime.datetime.fromisoformat(str(r[0])[:19]).timestamp()
        except Exception:  # noqa: BLE001
            continue
    resta = (t + FINESTRA) - ORA.timestamp()
    if resta > 0:
        vive.append((resta, r[1] if campo_k and len(r) > 1 else "?"))
    else:
        scadute += 1

print("\nvoci ancora RECUPERABILI: %d      gia' scadute: %d" % (len(vive), scadute))
if not vive:
    raise SystemExit(0)

print("\nQUANDO SCADONO le recuperabili")
soglie = [(6, "entro 6 ore"), (24, "entro 24 ore"), (48, "entro 2 giorni"),
          (96, "entro 4 giorni"), (168, "entro 7 giorni")]
prec = 0
for ore, eti in soglie:
    k = sum(1 for r, _k in vive if prec * 3600 < r <= ore * 3600)
    print("  %-16s %4d" % (eti, k))
    prec = ore

print("\nQUANTE DI QUESTE SONO PROBABILMENTE RITIRI SBAGLIATI")
print("(quota misurata nel doc 41: 10,2%% dopo il 25/08)")
n = len(vive)
print("  recuperabili ora: %d   ->   attesi sbagliati: ~%.0f" % (n, n * 0.102))
print("\n⚠️ La stima dice QUANTI, non QUALI. Per sapere quali bisogna leggerli,")
print("   e il restore richiede mandato: qui si misura soltanto.")
