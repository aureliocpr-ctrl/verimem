"""Non quanti ritiri sono sbagliati, ma QUALI - e quanto tempo resta.

Il banco gemello stima ~34 ritiri sbagliati fra i 336 recuperabili, usando la
quota del doc 41 (10,2%). Una stima non si puo' consegnare a chi deve decidere:
serve la LISTA.

La tabella `facts_undo_log` ha `pre_row_json`, che contiene la RIGA DEL FATTO
COM'ERA PRIMA del ritiro. Da li' si prende il testo ritirato, e dal fatto che
l'ha superseduto si prende il testo che l'ha sostituito: due testi che si
possono confrontare.

Criterio del doc 41, ereditato e dichiarato: due testi che condividono poco
lessico (jaccard basso) non parlano della stessa cosa, quindi la supersessione
ha cancellato un fatto che diceva ALTRO.

⚠️ Il criterio e' LESSICALE su un fenomeno semantico: sbaglia in entrambe le
direzioni, ed e' lo stesso limite dichiarato nel 41. La lista e' un elenco di
CANDIDATI da leggere, non un verdetto.
⚠️ Qui si MISURA soltanto: nessun restore, che richiede mandato.

SOLA LETTURA sullo store.
"""
import datetime
import json
import os
import re
import sqlite3

DB = os.path.expanduser(os.path.join("~", ".engram", "semantic", "semantic.db"))
ORA = datetime.datetime.now().timestamp()
FINESTRA = 7 * 86400
SOGLIA = 0.15          # la soglia del doc 41


def token(t):
    return {w for w in re.findall(r"[a-z0-9]+", str(t or "").lower()) if len(w) > 2}


def jaccard(a, b):
    ta, tb = token(a), token(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


con = sqlite3.connect("file:%s?mode=ro" % DB.replace(os.sep, "/"), uri=True)
righe = con.execute(
    "SELECT fact_id, pre_row_json, created_at FROM facts_undo_log "
    "WHERE op_type = 'supersede'").fetchall()
print("voci di supersessione nel registro di undo: %d" % len(righe))

candidati, senza_testo, fuori = [], 0, 0
for fid, pre, creato in righe:
    try:
        t = float(creato)
    except Exception:      # noqa: BLE001
        try:
            t = datetime.datetime.fromisoformat(str(creato)[:19]).timestamp()
        except Exception:  # noqa: BLE001
            continue
    resta = (t + FINESTRA) - ORA
    if resta <= 0:
        fuori += 1
        continue
    try:
        vecchio = (json.loads(pre) or {}).get("proposition")
    except Exception:      # noqa: BLE001
        vecchio = None
    r = con.execute(
        "SELECT proposition, superseded_by FROM facts WHERE id = ?", (fid,)).fetchone()
    if not vecchio or not r or not r[1]:
        senza_testo += 1
        continue
    n = con.execute(
        "SELECT proposition FROM facts WHERE id = ?", (r[1],)).fetchone()
    if not n:
        senza_testo += 1
        continue
    j = jaccard(vecchio, n[0])
    if j < SOGLIA:
        candidati.append((resta, j, fid, str(vecchio)[:96]))

con.close()
print("  gia' fuori finestra: %d      senza testo confrontabile: %d"
      % (fuori, senza_testo))
print("  CANDIDATI (jaccard < %.2f, i due testi parlano d'altro): %d"
      % (SOGLIA, len(candidati)))

candidati.sort()
print("\nI PIU' URGENTI (ordinati per tempo residuo)")
print("%-9s %-7s %-14s %s" % ("resta", "jaccard", "fact_id", "il fatto RITIRATO"))
for resta, j, fid, testo in candidati[:15]:
    print("%6.1f h  %6.3f  %-14s %s" % (resta / 3600.0, j, fid, testo))

entro24 = sum(1 for r, _j, _f, _t in candidati if r <= 86400)
entro48 = sum(1 for r, _j, _f, _t in candidati if r <= 2 * 86400)
print("\ndi questi candidati: %d scadono entro 24 ore, %d entro 48."
      % (entro24, entro48))
print("\n⚠️ CANDIDATI, non verdetti: il criterio e' lessicale su un fenomeno")
print("   semantico e sbaglia in entrambe le direzioni (limite gia' dichiarato")
print("   nel doc 41). Vanno LETTI. Il restore richiede mandato.")
