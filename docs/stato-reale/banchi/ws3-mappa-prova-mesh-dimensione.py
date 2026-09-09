"""Il controllo che può falsificare il reperto sul mesh.

Misurato: gli embedding dello store sono da 3072 byte (768 float32), mentre
`mesh_memory.EMBED_DIM` è 384 e la query filtra `length(embedding) = 1536` →
zero righe, sempre, in silenzio.

Ma se il modello di embedding fosse una scelta del MIO ambiente e il default del
prodotto fosse a 384, il difetto sarebbe mio e non del codice. Quindi: quale
modello ha scritto quelle righe, e qual è il default del prodotto?
"""
from __future__ import annotations

import os
import pathlib
import sqlite3
import sys
import tempfile

WT = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(WT))
tmp = pathlib.Path(tempfile.mkdtemp(prefix="ws3-dim-"))
os.environ["ENGRAM_DATA_DIR"] = str(tmp)
os.environ.pop("HIPPO_ENCODE_DELEGATE_ONLY", None)
from verimem import Memory  # noqa: E402
from verimem import mesh_memory as ME  # noqa: E402

m = Memory(str(tmp / "d.db"))
m.add("Il canone del capannone 12 e' 5900 euro.",
      source="Verbale: il canone del capannone 12 e' 5900 euro.", topic="d/x")
con = sqlite3.connect(f"file:{m.semantic.db_path}?mode=ro", uri=True)
for fid, mod, n in con.execute(
        "SELECT id, embedding_model, length(embedding) FROM facts "
        "WHERE embedding IS NOT NULL LIMIT 3"):
    print(f"  fatto {fid[:12]} · modello '{mod}' · embedding {n} byte = {n // 4} float32")
con.close()

print("\n  mesh_memory.EMBED_DIM =", ME.EMBED_DIM,
      "→ la query filtra length(embedding) =", ME.EMBED_DIM * 4, "byte")

print("\n=== il default del prodotto, letto dal codice ===")
import subprocess  # noqa: E402

for patt in ("HIPPO_EMBED_MODEL", "multilingual-e5", "all-MiniLM", "EMBED_MODEL"):
    out = subprocess.run(
        ["git", "grep", "-n", "--", patt, "verimem/"],
        cwd=str(WT), capture_output=True, text=True, encoding="utf-8", errors="replace")
    righe = [r for r in out.stdout.splitlines() if "test" not in r][:3]
    print(f"  {patt}:")
    for r in righe:
        print("   ", r[:150])

print("\n=== lo store di casa (sola lettura): che dimensione hanno LI'? ===")
casa = r"C:\Users\aurel\.engram\semantic\semantic.db"
try:
    con = sqlite3.connect(f"file:{casa}?mode=ro", uri=True, timeout=5)
    for mod, n, quanti in con.execute(
            "SELECT embedding_model, length(embedding), COUNT(*) FROM facts "
            "WHERE embedding IS NOT NULL GROUP BY embedding_model, length(embedding) "
            "ORDER BY COUNT(*) DESC LIMIT 5"):
        print(f"  modello '{mod}' · {n} byte ({(n or 0) // 4} float32) · {quanti} fatti")
    con.close()
except Exception as e:  # noqa: BLE001
    print("  non leggibile:", type(e).__name__, str(e)[:80])
