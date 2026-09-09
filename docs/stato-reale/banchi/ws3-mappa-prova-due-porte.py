"""IL CONTROLLO CHE DECIDE LA PORTATA DEL REPERTO.

Sulla via dell'ingest, `_grounds` ha ammesso **3 fatti inventati su 3** — cose
che il dialogo non dice — e `ingest_conversation` li ha memorizzati.

Ma il gate della scrittura ordinaria (`Memory.add(source=…)`) è un'altra strada,
con un'altra catena di controlli. Se `add` li QUARANTINA, allora il reperto è
preciso: **due porte, due severità**. Se li ammette anche lui, il reperto
riguarda il cuore del prodotto e va detto in modo diverso.

Stessa fonte, stessi tre fatti inventati, stessi tre detti: si confronta.
"""
from __future__ import annotations

import os
import pathlib
import sys
import tempfile

WT = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(WT))
tmp = pathlib.Path(tempfile.mkdtemp(prefix="ws3-2porte-"))
os.environ["ENGRAM_DATA_DIR"] = str(tmp)
os.environ.pop("HIPPO_ENCODE_DELEGATE_ONLY", None)
from verimem import Memory  # noqa: E402
from verimem import conversation_ingest as CI  # noqa: E402

FONTE = ("Il canone del capannone 12 e' 5900 euro al mese, "
         "e la consegna e' prevista per il 3 marzo.")
DETTI = ["Il canone del capannone 12 e' 5900 euro.",
         "La consegna del capannone 12 e' prevista per il 3 marzo."]
INVENTATI = ["Il capannone 12 e' stato venduto nel 2019.",
             "Il capannone 12 ha una superficie di 400 metri quadri.",
             "Il proprietario del capannone 12 si chiama Mario Rossi."]
CONTRADDETTI = ["Il canone del capannone 12 e' 9999 euro."]

m = Memory(str(tmp / "p.db"))
print(f"{'CASO':56} {'add()':>22}   {'_grounds (ingest)':>22}")
print("-" * 104)
for gruppo, elenco in (("DETTO", DETTI), ("INVENTATO", INVENTATI),
                       ("CONTRADDETTO", CONTRADDETTI)):
    for p in elenco:
        r = m.add(p, source=FONTE, topic=f"due/{gruppo.lower()}")
        ok, s = CI._grounds(f"assistant: {FONTE}", p)
        print(f"{gruppo:13} {p[:40]!r:44} "
              f"{str(r.get('status')):>13} {round(float(r.get('grounding_score') or 0), 1):>7}   "
              f"{str(ok):>13} {round(float(s), 1):>7}")

print("\nconteggio finale nello store (chi e' servito e chi no):")
for stato in ("model_claim", "quarantined"):
    n = len([f for f in m.get_all(limit=100) if f.get("status") == stato])
    print(f"  {stato:14}: {n}")
serviti = m.search("capannone 12", k=10)
print("  serviti da search:", len(serviti))
for h in serviti:
    print("   ", str(h.get("text"))[:60])
