"""Il controllo che può falsificarmi: `_blocking_layers` include `L4-skipped`
fra i layer che «hanno AGITO» sulla scrittura, ma il commento di
`_BLOCK_LAYER_PRIORITY`, dieci righe sopra, dice che `L4-skipped` NON è un
blocco — è l'avviso «il giudice non è girato».

Sulla funzione pura l'ho già visto (out: ['L1', 'L4-skipped', 'L4.1']). Quella è
una misura al livello sbagliato: decide il prodotto, non la funzione. Qui misuro
ALLA PORTA — una scrittura vera che viene fermata mentre il giudice non gira — e
guardo il `by_layer` del contatore pubblico `trust_stats()`, che è ciò che
l'utente legge.

Se `by_layer` porta `L4-skipped`, l'avviso si prende il merito di un blocco che
non ha causato. Se non lo porta, la mia lettura è sbagliata e lo scrivo.
"""
import os
import pathlib
import sys
import tempfile

WT = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(WT))
tmp = pathlib.Path(tempfile.mkdtemp(prefix="ws3-ledger-"))
os.environ["ENGRAM_DATA_DIR"] = str(tmp)
os.environ.pop("HIPPO_ENCODE_DELEGATE_ONLY", None)
from verimem import Memory  # noqa: E402

m = Memory(str(tmp / "l.db"))
print("guardia:", Memory.__module__, "|", sys.modules["verimem.client"].__file__)

print("\n=== A. scrittura SENZA fonte che il gate ferma (il giudice non gira)")
r = m.add("Il sistema e' sicuro al 100% e non ha mai avuto un incidente.",
          topic="l/a")
print("  status:", r.get("status"), "| stored:", r.get("stored"))
print("  warnings (layer):", [w.get("layer") for w in (r.get("warnings") or [])])
adj = r.get("adjudication") or {}
print("  adjudication.evidence_class:", adj.get("evidence_class"),
      "| reason:", str(adj.get("reason"))[:90])

print("\n=== B. scrittura CON fonte e un numero che la fonte non contiene")
F = "Verbale del 3 marzo: il canone del capannone 12 e' 5900 euro."
r2 = m.add("Il canone del capannone 12 e' 7300 euro.", source=F, topic="l/b")
print("  status:", r2.get("status"))
print("  warnings (layer):", [w.get("layer") for w in (r2.get("warnings") or [])])

print("\n=== C. una scrittura buona, per avere anche il lato ammesso")
r3 = m.add("Il canone del capannone 12 e' 5900 euro.", source=F, topic="l/c")
print("  status:", r3.get("status"))
print("  warnings (layer):", [w.get("layer") for w in (r3.get("warnings") or [])])

print("\n=== IL CONTATORE PUBBLICO: trust_stats()")
ts = m.trust_stats()
print("  ledger:", ts.get("ledger"))
print("  by_layer:", ts.get("by_layer"))
bl = ts.get("by_layer") or {}
print("\n  >>> 'L4-skipped' compare fra i layer del contatore?",
      "SI" if any("L4-skipped" in k for k in bl) else "NO")
print("  >>> layer presenti:", sorted(bl))
