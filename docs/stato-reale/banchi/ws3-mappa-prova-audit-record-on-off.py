"""L'ultima delle 80: `_audit_record` (client.py:2771) — «appende il verdetto
della scrittura alla traccia opt-in (VERIMEM_AUDIT_LOG). Non fa nulla quando è
spenta; non solleva mai — persistere un record di audit non deve mai rompere la
scrittura di memoria che registra».

Due lati, perché «non fa nulla quando è spenta» è metà della promessa:
  OFF -> il file gemello adjudications.db NON deve nascere;
  ON  -> deve nascere e contenere il verdetto della scrittura.
"""
import os
import pathlib
import sqlite3
import sys
import tempfile

WT = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(WT))
FONTE = "Verbale del 3 marzo: il canone del capannone 12 e' 5900 euro."


def giro(acceso: bool):
    d = pathlib.Path(tempfile.mkdtemp(prefix="ws3-adt-"))
    os.environ["ENGRAM_DATA_DIR"] = str(d)
    if acceso:
        os.environ["VERIMEM_AUDIT_LOG"] = "1"
    else:
        os.environ.pop("VERIMEM_AUDIT_LOG", None)
    from verimem import Memory
    m = Memory(str(d / "s.db"))
    m.add("Il canone del capannone 12 e' 5900 euro.", source=FONTE, topic="ad/ok")
    m.add("Il canone del capannone 12 e' 7300 euro.", source=FONTE, topic="ad/ko")
    p = d / "adjudications.db"
    print(f"\nVERIMEM_AUDIT_LOG {'ON ' if acceso else 'OFF'} -> adjudications.db esiste:",
          p.exists())
    if not p.exists():
        return
    con = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
    tab = [r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")]
    print("  tabelle:", tab)
    for t in tab:
        n = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]  # noqa: S608
        print(f"  {t}: {n} righe")
        if n:
            cols = [c[1] for c in con.execute(f"PRAGMA table_info({t})")]
            r = con.execute(f"SELECT * FROM {t} LIMIT 2").fetchall()  # noqa: S608
            for riga in r:
                d2 = dict(zip(cols, riga, strict=False))
                print("   ", {k: str(v)[:46] for k, v in list(d2.items())[:7]})
    con.close()


giro(False)
giro(True)
