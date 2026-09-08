"""Isola la causa dello 0 di LIST_ALL: e' l'enumerazione rotta, o e' il plurale
che non combacia col singolare del corpus? Una variabile per volta."""
import os
import pathlib
import sys
import tempfile

WT = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(WT))
tmp = pathlib.Path(tempfile.mkdtemp(prefix="ws3-listall-"))
os.environ["ENGRAM_DATA_DIR"] = str(tmp)
sys.path.insert(0, str(WT))
from verimem import Memory  # noqa: E402
from verimem.query_intent import classify_query_intent, content_terms  # noqa: E402

m = Memory(str(tmp / "l.db"))
m.add("Il canone del capannone 12 e' 5900 euro.", source="Contratto: il canone del capannone 12 e' 5900 euro.", topic="t")
m.add("Il capannone 12 e' a Prato.", source="Anagrafica: il capannone 12 si trova a Prato.", topic="t")

for q in ("elenca tutti i capannoni", "elenca tutti i capannone",
          "elenca tutto sul capannone", "list all capannone", "elenca tutti i fatti"):
    intent = classify_query_intent(q)
    termini = content_terms(q)
    r = m.ask(q, k=5)
    n = len(r.get("results", [])) if "results" in r else r.get("count")
    print(f"{q!r:38s} intent={str(intent):12s} termini={termini} -> {n}")
