"""Chiude `briefing.py` (3) e `mesh_memory.py` (8) con i controlli che mancavano.

Nel giro precedente `_is_call_telemetry_episode` diceva False su cinque testi:
letta la regex (`_call_telemetry.py:17`), il formato è `[<llm>-call …]` a inizio
riga — i miei cinque casi non lo erano. Qui c'è il **controllo positivo col
formato vero** accanto a quello che deve restare spento.

E `local_topk_embeddings` aveva reso 0 righe su uno store con 2 fatti: prima di
scrivere «non funziona» conto gli embedding che ci sono davvero nel database.
"""
from __future__ import annotations

import os
import pathlib
import sqlite3
import sys
import tempfile

WT = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(WT))
tmp = pathlib.Path(tempfile.mkdtemp(prefix="ws3-mesh-"))
os.environ["ENGRAM_DATA_DIR"] = str(tmp)
os.environ.pop("HIPPO_ENCODE_DELEGATE_ONLY", None)
import numpy as np  # noqa: E402

from verimem import Memory  # noqa: E402
from verimem import briefing as BR  # noqa: E402
from verimem import mesh_memory as ME  # noqa: E402


class _Ep:
    def __init__(self, t):
        self.task_text = t


print("=== briefing: il riconoscitore col FORMATO VERO accanto a quello spento")
for testo in ("[gemini-call 1.2s] ask_gemini(prompt=…)",
              "[agy-call] ok",
              "[CLAUDE-CALL 0.3s] ask_claude",
              "  [kimi-call] con spazi davanti",
              "cross-LLM call to gemini: ok",
              "ho scritto la mappa di client.py",
              "[deploy-call] non e' un llm"):
    print(f"  {testo!r:44} -> {BR._is_call_telemetry_episode(_Ep(testo))}")

print("\n=== mesh: quanti embedding ci sono DAVVERO nel db")
m = Memory(str(tmp / "s.db"))
F = "Verbale del 3 marzo: il canone del capannone 12 e' 5900 euro."
m.add("Il canone del capannone 12 e' 5900 euro.", source=F, topic="me/x")
m.add("Il capannone 12 e' in via Roma.", source="Il capannone 12 e' in via Roma.",
      topic="me/y")
con = sqlite3.connect(f"file:{m.semantic.db_path}?mode=ro", uri=True)
cols = [c[1] for c in con.execute("PRAGMA table_info(facts)")]
print("  colonne di facts che parlano di vettori:",
      [c for c in cols if "emb" in c or "vec" in c])
n_tot = con.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
n_emb = con.execute(
    "SELECT COUNT(*) FROM facts WHERE embedding IS NOT NULL").fetchone()[0] \
    if "embedding" in cols else -1
print(f"  fatti: {n_tot} · con embedding non nullo: {n_emb}")
if n_emb > 0:
    blob = con.execute(
        "SELECT embedding FROM facts WHERE embedding IS NOT NULL LIMIT 1").fetchone()[0]
    print("  lunghezza del blob:", len(blob), "byte →",
          len(blob) / 4, "float32")
con.close()

print("\n=== mesh: le funzioni pure")
a = np.zeros(384, dtype=np.float32)
a[0] = 1.0
b = np.zeros(384, dtype=np.float32)
b[1] = 1.0
mezzo = (a + b) / np.linalg.norm(a + b)
print("  _cosine(uguali):", ME._cosine(a.tobytes(), a.tobytes()),
      "| ortogonali:", ME._cosine(a.tobytes(), b.tobytes()),
      "| a 45 gradi:", round(float(ME._cosine(a.tobytes(), mezzo.tobytes())), 4))
print("  _vec_bus():", ME._vec_bus().__name__)
r = ME.local_topk_embeddings(str(m.semantic.db_path), a.tobytes(), 3)
print("  local_topk_embeddings(vettore artificiale):", len(r), "righe")
if r:
    print("    prima riga:", [type(x).__name__ for x in r[0]], "score",
          round(float(r[0][2]), 4))
try:
    fusa = ME.mesh_resonant_merge(a.tobytes(), [(("id1"), a.tobytes(), 1.0)],
                                  [(("id2"), b.tobytes(), 0.0)], 0.5)
    print("  mesh_resonant_merge:", str(fusa)[:140])
except Exception as e:  # noqa: BLE001
    print("  mesh_resonant_merge ->", type(e).__name__, str(e)[:120])
