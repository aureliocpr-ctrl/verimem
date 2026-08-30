import os
import sqlite3

from verimem.client import Memory  # noqa: E402 - dopo HIPPO_DATA_DIR, altrimenti isolamento salta

DB = os.path.expanduser("~/.engram/semantic/semantic.db")
c = sqlite3.connect("file:{}?mode=ro".format(DB.replace(os.sep, "/")), uri=True)
tot = c.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
vivi = c.execute("SELECT COUNT(*) FROM facts WHERE superseded_by IS NULL").fetchone()[0]
c.close()
salvato, drift = 13795, Memory._FLOOR_DRIFT
soglia = max(1, salvato) * drift
print(f"_FLOOR_DRIFT = {drift}  =>  tolleranza = {soglia:.1f} fatti")
for nome, n in (("facts TOTALI", tot), ("facts VIVI", vivi)):
    d = abs(n - salvato)
    esito = "USA IL SALVATO" if d <= soglia else "RICALCOLA"
    print(f"{nome:<14s} = {n:6d}   scarto dal salvato(13795) = {n - salvato:+5d}   "
          f"{esito}   margine residuo = {soglia - d:.0f}")
