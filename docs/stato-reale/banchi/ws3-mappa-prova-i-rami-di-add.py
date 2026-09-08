"""Blocco 5 della mappa: I RAMI di `Memory.add`, cioè dove il prodotto decide
cosa entra in memoria. Ogni ramo con la stessa coppia (claim falso, fonte che
lo smentisce), così l'unica variabile è il ramo.

I claim del README coinvolti: 194 («`Memory(preset="permissive")` /
`validate="fast"` skip the moat entirely»), 172 («the write-gate checks
*source ⊢ fact*»), e le istruzioni del server MCP («ON EVERY WRITE … a lexical
screen. ONE EXCEPTION … `meta_narrative=True` … skips that screen»).
"""
import os
import pathlib
import sys
import tempfile

WT = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(WT))
tmp = pathlib.Path(tempfile.mkdtemp(prefix="ws3-rami-"))
os.environ["ENGRAM_DATA_DIR"] = str(tmp)
os.environ.pop("HIPPO_ENCODE_DELEGATE_ONLY", None)
from verimem import Memory  # noqa: E402

FONTE = "Verbale del 3 marzo: il canone del capannone 12 e' 5900 euro."
FALSO = "Il canone del capannone 12 e' 7300 euro."
VERO = "Il canone del capannone 12 e' 5900 euro."
AUTO = "La funzionalita' e' stata implementata e verificata."


def riga(nome, r):
    if not isinstance(r, dict):
        print(f"  {nome:34s} -> {type(r).__name__} {str(r)[:60]}")
        return
    w = r.get("warnings") or r.get("anti_confab_warnings") or []
    layers = [x.get("layer") for x in w if isinstance(x, dict)]
    print(f"  {nome:34s} -> status={str(r.get('status')):12s} g={str(r.get('grounding_score'))[:7]:8s} "
          f"stored={r.get('stored')} layers={layers}")


print("=== A) il falso, con la fonte che lo smentisce, ramo per ramo")
m = Memory(str(tmp / "a.db"))
riga("default", m.add(FALSO, source=FONTE, topic="r/a1"))
try:
    riga("gate_mode='reject'", m.add(FALSO, source=FONTE, topic="r/a2", gate_mode="reject"))
except Exception as e:  # noqa: BLE001
    print(f"  {'gate_mode=reject':34s} -> ECCEZIONE {type(e).__name__}: {str(e)[:70]}")
riga("validate='fast'  [README:194]", m.add(FALSO, source=FONTE, topic="r/a3", validate="fast"))
riga("ground=False", m.add(FALSO, source=FONTE, topic="r/a4", ground=False))
riga("SENZA source", m.add(FALSO, topic="r/a5"))
riga("il VERO (controllo)", m.add(VERO, source=FONTE, topic="r/a6"))

print("\n=== B) preset permissive [README:194: «skip the moat entirely»]")
try:
    mp = Memory(str(tmp / "b.db"), preset="permissive")
    riga("preset=permissive, falso", mp.add(FALSO, source=FONTE, topic="r/b1"))
except Exception as e:  # noqa: BLE001
    print(f"  preset=permissive -> ECCEZIONE {type(e).__name__}: {str(e)[:90]}")

print("\n=== C) lo screen lessicale sulla self-claim, e l'eccezione dichiarata")
mc = Memory(str(tmp / "c.db"))
riga("self-claim SENZA source", mc.add(AUTO, topic="r/c1"))
riga("self-claim + meta_narrative=True", mc.add(AUTO, topic="r/c2", meta_narrative=True))
riga("self-claim + verified_by", mc.add(AUTO, topic="r/c3", verified_by=["pytest: 8 passed"]))

print("\n=== D) asserted_at, il campo che il commento dice mai valorizzato")
md = Memory(str(tmp / "d.db"))
riga("con asserted_at", md.add(VERO, source=FONTE, topic="r/d1", asserted_at=1_780_000_000.0))
got = md.get((md.add(VERO, source=FONTE, topic="r/d2", asserted_at=1_780_000_001.0) or {}).get("id"))
print("  rilettura: asserted_at =", (got or {}).get("asserted_at"))
