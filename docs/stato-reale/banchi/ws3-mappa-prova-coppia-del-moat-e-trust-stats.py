"""Chiude i due debiti: `esito_del_moat(gate, warnings, source=…)` vuole il
GateResult (non il dict della ricevuta) e `chi_ha_quarantinato(moat, warnings)`
vuole la STRINGA che la prima restituisce — si compongono. E misura
`trust_stats`, il claim README:284 («persistent counters of what the gate
actually did»)."""
import os
import pathlib
import sys
import tempfile

WT = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(WT))
tmp = pathlib.Path(tempfile.mkdtemp(prefix="ws3-moatpair-"))
os.environ["ENGRAM_DATA_DIR"] = str(tmp)
os.environ.pop("HIPPO_ENCODE_DELEGATE_ONLY", None)
from verimem import Memory  # noqa: E402
from verimem.anti_confab_gate import run_validation_gate  # noqa: E402
from verimem.client import chi_ha_quarantinato, esito_del_moat  # noqa: E402

FONTE = "Verbale del 3 marzo: il canone del capannone 12 e' 5900 euro."
CASI = [
    ("vero, con fonte", "Il canone del capannone 12 e' 5900 euro.", FONTE),
    ("falso, con fonte", "Il canone del capannone 12 e' 7300 euro.", FONTE),
    ("self-claim senza fonte", "La funzionalita' e' stata implementata e verificata.", None),
    ("nota libera senza fonte", "Domani piove.", None),
]
print("=== esito_del_moat + chi_ha_quarantinato, composti come vuole la firma")
for nome, prop, src in CASI:
    r = run_validation_gate(proposition=prop, source=src, grounding_llm=None,
                            ground_write=bool(src), verified_by=None, topic=None, agent=None)
    w = r.warnings or []
    moat = esito_del_moat(r, w, source=src)
    chi = chi_ha_quarantinato(moat, w)
    print(f"  {nome:24s} action={r.action:10s} moat={moat!r:22s} chi={chi!r}")

print("\n=== trust_stats  [README:284]")
m = Memory(str(tmp / "ts.db"))
m.add("Il canone del capannone 12 e' 5900 euro.", source=FONTE, topic="ts/1")
m.add("Il canone del capannone 12 e' 7300 euro.", source=FONTE, topic="ts/2")
for nome in ("trust_stats", "stats"):
    try:
        v = getattr(m, nome)()
        print(f"  {nome}(): {type(v).__name__} {str(v)[:220]}")
    except AttributeError:
        print(f"  {nome}(): ASSENTE su Memory")
    except Exception as e:  # noqa: BLE001
        print(f"  {nome}(): ECCEZIONE {type(e).__name__} {str(e)[:120]}")
