"""Correzione di un errore MIO: la verifica precedente stampava il BASENAME, e
sotto `.engram` ci sono sei file che si chiamano `semantic.db` (store, dreams,
backups). «semantic.db con 4 scritture recenti» non identifica nessun file: il
db di casa, interrogato per nome pieno, ne ha ZERO nell'ultima ora.

Qui stampo il PATH COMPLETO di ogni db che ha scritture recenti, e le righe."""
import glob
import os
import sqlite3
import time

BASE = r"C:\Users\aurel\.engram"
ORA = time.time()
print("adesso:", time.strftime("%H:%M:%S", time.localtime(ORA)))
trovati = 0
for p in sorted(glob.glob(os.path.join(BASE, "**", "*.db"), recursive=True)):
    try:
        con = sqlite3.connect(f"file:{p}?mode=ro", uri=True, timeout=5)
    except Exception:  # noqa: BLE001
        continue
    try:
        tab = {r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        if "facts" not in tab:
            continue
        cols = {r[1] for r in con.execute("PRAGMA table_info(facts)")}
        if "created_at" not in cols:
            continue
        n = con.execute("SELECT COUNT(*) FROM facts WHERE created_at > ?",
                        (ORA - 3600,)).fetchone()[0]
        if not n:
            continue
        trovati += 1
        tot = con.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
        print(f"\n>>> {p}  (totale {tot}, recenti {n})")
        testo = "text" if "text" in cols else "proposition"
        campi = [c for c in ("created_at", "topic", "status", testo) if c in cols]
        for r in con.execute(
                f"SELECT {', '.join(campi)} FROM facts WHERE created_at > ? "
                f"ORDER BY created_at DESC LIMIT 8", (ORA - 3600,)):
            d = dict(zip(campi, r))
            t = time.strftime("%H:%M:%S", time.localtime(float(d["created_at"])))
            print(f"    {t} | {str(d.get('topic'))[:38]:38} | "
                  f"{str(d.get('status'))[:11]:11} | {str(d.get(testo))[:64]}")
    except Exception as e:  # noqa: BLE001
        print(f"  {p}: ERRORE {type(e).__name__}")
    finally:
        con.close()
print("\nDB con scritture nell'ultima ora:", trovati)
