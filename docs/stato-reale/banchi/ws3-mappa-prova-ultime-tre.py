"""Le ultime tre di `client.py`: `_source_trust_book`, `record_decision`,
`Risultati.__init__`."""
from __future__ import annotations

import os
import pathlib
import sys
import tempfile

WT = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(WT))
tmp = pathlib.Path(tempfile.mkdtemp(prefix="ws3-tre-"))
os.environ["HIPPO_DATA_DIR"] = str(tmp)
os.environ["ENGRAM_DATA_DIR"] = str(tmp)
os.environ.pop("HIPPO_ENCODE_DELEGATE_ONLY", None)
from verimem import Memory  # noqa: E402
from verimem.client import Risultati  # noqa: E402

F = "Verbale del 3 marzo: il canone del capannone 12 e' 5900 euro."
m = Memory(str(tmp / "t.db"))
m.add("Il canone del capannone 12 e' 5900 euro.", source=F, topic="t/ok")
m.add("Il canone del capannone 12 e' 7300 euro.", source=F, topic="t/ko")

print("=== Memory._source_trust_book: il libro della fiducia delle fonti")
libro = m._source_trust_book()
print("  tipo:", type(libro).__name__)
print("  metodi pubblici:", [x for x in dir(libro) if not x.startswith("_")][:12])
print("  fiducia della fonte prima di osservazioni:", m.source_trust(F))
m.source_trust_observe(contradiction=F)
print("  dopo una contraddizione:", m.source_trust(F))
libro2 = m._source_trust_book()
print("  la seconda chiamata rende lo STESSO oggetto (cache):", libro is libro2)

print("\n=== Memory.record_decision + why_decision")
d = m.record_decision("uso Postgres per l'analytics", topic="t/dec")
print("  record_decision ->", repr(d)[:80])
print("  why_decision('Postgres') ->", str(m.why_decision("Postgres"))[:170])
print("  why_decision('argomento mai deciso') ->", m.why_decision("cammelli"))

print("\n=== Risultati.__init__: la lista dei risultati con gli AVVISI attaccati")
hits = m.search("canone capannone", k=5)
print("  tipo di ritorno di search:", type(hits).__name__,
      "· e' una lista:", isinstance(hits, list))
print("  quanti serviti:", len(hits))
for campo in ("sotto_il_pavimento", "trattenuti", "scaduti", "nascosti_per_eta"):
    print(f"  attributo {campo:20}: {str(getattr(hits, campo, 'ASSENTE'))[:80]}")
vuoto = Risultati()
print("  Risultati() vuoto:", list(vuoto), "· trattenuti:",
      getattr(vuoto, "trattenuti", "ASSENTE"))
pieno = Risultati([{"text": "uno"}], sotto_il_pavimento={"quanti": 3})
print("  Risultati con avviso:", len(pieno), "elementi · sotto_il_pavimento:",
      getattr(pieno, "sotto_il_pavimento", None))
print("  >>> resta una lista vera (si itera e si conta):",
      [x.get("text") for x in pieno])
