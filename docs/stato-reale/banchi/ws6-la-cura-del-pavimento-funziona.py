"""La cura proposta nel doc 48 funziona davvero?

Proposta: cancellare `semantic.db.floor.json` e lasciare che il prodotto
ricalcoli. Qui la verifico SU UNA COPIA in tempdir — lo store di Aurelio non
viene toccato in nessun modo.

Sequenza: copia lo store -> legge il floor persistito -> cancella il file
(NELLA COPIA) -> richiama la stessa funzione -> confronta.
"""
import os
import shutil
import tempfile
from pathlib import Path

# HIPPO_DATA_DIR ha precedenza su ENGRAM_DATA_DIR: va impostata PRIMA degli
# import del prodotto, e le altre vanno tolte o non isolano.
TMP = Path(tempfile.mkdtemp(prefix="ws6-floor-"))
os.environ["HIPPO_DATA_DIR"] = str(TMP)
os.environ.pop("ENGRAM_DATA_DIR", None)
os.environ.pop("VERIMEM_DATA_DIR", None)

SRC = Path(os.path.expanduser("~/.engram/semantic/semantic.db"))
DST_DIR = TMP / "semantic"
DST_DIR.mkdir(parents=True, exist_ok=True)
DST = DST_DIR / "semantic.db"
print("copia dello store in %s" % DST)
shutil.copy2(SRC, DST)
floor_src = SRC.parent / "semantic.db.floor.json"
floor_dst = DST_DIR / "semantic.db.floor.json"
if floor_src.exists():
    shutil.copy2(floor_src, floor_dst)
print("  copiati: db %.1f MB, floor.json %s"
      % (DST.stat().st_size / 1e6, "sì" if floor_dst.exists() else "no"))

from verimem.client import Memory  # noqa: E402  (dopo le env, di proposito)

m = Memory(str(DST))
print("\n1) col file presente (contenuto: %s)" % floor_dst.read_text().strip())
print("   _auto_relevance_floor() -> %r" % m._auto_relevance_floor())

floor_dst.unlink()
print("\n2) file cancellato NELLA COPIA")
m2 = Memory(str(DST))          # istanza nuova: nessuna cache in memoria
val = m2._auto_relevance_floor()
print("   _auto_relevance_floor() -> %r" % val)
print("   il file e' stato riscritto: %s" % floor_dst.exists())
if floor_dst.exists():
    print("   nuovo contenuto: %s" % floor_dst.read_text().strip())

print("\n=> la cura %s"
      % ("FUNZIONA: il pavimento torna a un valore utile"
         if isinstance(val, float) and val > 0.1
         else "NON basta: il ricalcolo non produce un pavimento utile"))
print("\nlo store di Aurelio non e' stato toccato; la copia sta in %s" % TMP)
