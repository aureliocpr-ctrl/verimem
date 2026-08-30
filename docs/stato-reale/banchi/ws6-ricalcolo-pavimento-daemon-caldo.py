"""Che valore prende il pavimento SE ricalcola ADESSO, con il daemon caldo?
Su COPIA in tempdir. Lo store di Aurelio non viene toccato."""
import os
import shutil
import tempfile

tmp = tempfile.mkdtemp(prefix="ws6_floor_")
os.environ["HIPPO_DATA_DIR"] = tmp
for v in ("ENGRAM_DATA_DIR", "VERIMEM_DATA_DIR"):
    os.environ.pop(v, None)
SRC = os.path.expanduser("~/.engram/semantic/semantic.db")
DST = os.path.join(tmp, "semantic.db")
shutil.copy2(SRC, DST)
print("copia in:", DST)
from verimem.client import Memory  # noqa: E402 - dopo HIPPO_DATA_DIR, altrimenti isolamento salta

m = Memory(DST)
print("fatti vivi sulla copia:", m.semantic.count())
f = m._floor_file()
print("floor.json ereditato dalla copia?", f.exists())
if f.exists():
    f.unlink()
    print("  -> cancellato SULLA COPIA")
m._floor_cache = None
val = m._auto_relevance_floor()
print(f"\nPAVIMENTO RICALCOLATO ORA (daemon caldo) = {val!r}")
print("valore misurato ieri sera nel doc 48      = 0.8881")
print("banda dentro-dominio misurata da ws2      = 0.840 - 0.868")
if val:
    print("=> il ricalcolo sta %s il massimo delle risposte buone (0.868)"
          % ("SOPRA" if val > 0.868 else "SOTTO"))
print("\nfloor.json VERO di Aurelio, riletto adesso:")
print(" ", open(os.path.expanduser("~/.engram/semantic/semantic.db.floor.json")).read())
