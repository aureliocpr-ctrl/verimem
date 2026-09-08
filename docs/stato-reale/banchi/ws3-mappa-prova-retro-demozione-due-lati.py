"""Il controllo a DUE LATI su `_retro_demote_source`: prende i fatti che citano
la fonte in `verified_by` con uno dei prefissi (`source-doc`, `source`, `src`,
`doc`, `file`) e NON quelli scritti con `add(source=…)`, che lasciano
`verified_by` vuoto e mettono la fonte in `source_signature`.

Senza il lato positivo, «non ha quarantinato nulla» potrebbe voler dire «la
funzione non funziona»; con il lato positivo si vede che funziona e che il
canale principale del README non è coperto."""
import os
import pathlib
import sys
import tempfile

WT = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(WT))
tmp = pathlib.Path(tempfile.mkdtemp(prefix="ws3-retro-"))
os.environ["ENGRAM_DATA_DIR"] = str(tmp)
os.environ.pop("HIPPO_ENCODE_DELEGATE_ONLY", None)
from verimem import Memory  # noqa: E402

F = "Verbale del 3 marzo: il canone del capannone 12 e' 5900 euro."
m = Memory(str(tmp / "r.db"))

# lato A: il canale del README — add(source=…)
a = m.add("Il canone del capannone 12 e' 5900 euro.", source=F, topic="r/a")
# lato B: la fonte citata in verified_by col prefisso che la funzione cerca
b = m.add("La consegna e' del 3 marzo.", source=F, topic="r/b",
          verified_by=[f"source:{F}:sha256"])


def stato(r):
    return (m.get(r.get("id")) or {}).get("status")


def vb(r):
    return (m.get(r.get("id")) or {}).get("verified_by")


print("PRIMA:")
print("  A (add source=)          status:", stato(a), "· verified_by:", vb(a))
print("  B (verified_by 'source:')status:", stato(b), "· verified_by:", str(vb(b))[:60])

m._retro_demote_source(F)

print("\nDOPO _retro_demote_source(F):")
print("  A (canale del README)    status:", stato(a))
print("  B (verified_by col prefisso) status:", stato(b))

m._rehabilitate_source(F)
print("\nDOPO _rehabilitate_source(F):")
print("  A:", stato(a), "· B:", stato(b))
