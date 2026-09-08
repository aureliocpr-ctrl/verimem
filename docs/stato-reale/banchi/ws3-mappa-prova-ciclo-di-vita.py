"""Blocco 4 della mappa di client.py sul tip 20257636: il CICLO DI VITA di un
fatto dall'SDK — add, get, forget/delete, restore, supersede, pin — piu'
open_memory e le funzioni di soglia. Store temporaneo con path esplicito."""
import os
import pathlib
import sys
import tempfile

WT = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(WT))
tmp = pathlib.Path(tempfile.mkdtemp(prefix="ws3-mappa4-"))
os.environ["ENGRAM_DATA_DIR"] = str(tmp)
os.environ.pop("HIPPO_ENCODE_DELEGATE_ONLY", None)
import verimem  # noqa: E402
from verimem import Memory  # noqa: E402
from verimem.client import open_memory  # noqa: E402

print("IMPORT DA", verimem.__file__)
m = Memory(str(tmp / "m4.db"))
FONTE = "Verbale del 3 marzo: il canone del capannone 12 e' 5900 euro."
r = m.add("Il canone del capannone 12 e' 5900 euro.", source=FONTE, topic="mappa/ciclo")
fid = r.get("id")
print("add ->", r.get("status"), fid)

for nome, chiamata in (
    ("get(id)", lambda: m.get(fid)),
    ("count()", lambda: m.count()),
    ("topics()", lambda: m.topics()),
    ("recent(k=3)", lambda: m.recent(3) if hasattr(m, "recent") else "ASSENTE"),
    ("stats()", lambda: m.stats() if hasattr(m, "stats") else "ASSENTE"),
    ("health()", lambda: m.health() if hasattr(m, "health") else "ASSENTE"),
):
    try:
        v = chiamata()
        s = str(v)
        print(f"\n--- {nome}: {type(v).__name__}  {s[:180]}")
    except Exception as e:  # noqa: BLE001
        print(f"\n--- {nome}: ECCEZIONE {type(e).__name__}: {str(e)[:150]}")

print("\n--- open_memory(): apre lo store condiviso da CLI/MCP/SDK?")
try:
    m2 = open_memory()
    print("   tipo:", type(m2).__name__, "· stesso oggetto di Memory()?", isinstance(m2, Memory))
except Exception as e:  # noqa: BLE001
    print("   ECCEZIONE:", type(e).__name__, str(e)[:140])

print("\n--- forget/delete: come si toglie un fatto?")
for nome in ("forget", "delete", "fact_forget", "remove"):
    print(f"   Memory.{nome}: {'PRESENTE' if hasattr(m, nome) else 'ASSENTE'}")
try:
    if hasattr(m, "forget"):
        out = m.forget(fid)
        print("   forget(id) ->", str(out)[:120])
        print("   get(id) dopo forget ->", str(m.get(fid))[:80])
except Exception as e:  # noqa: BLE001
    print("   forget ECCEZIONE:", type(e).__name__, str(e)[:140])
