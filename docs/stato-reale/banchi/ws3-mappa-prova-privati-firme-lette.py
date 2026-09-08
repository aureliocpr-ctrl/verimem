"""Blocco 8, seconda passata: le stesse funzioni chiamate con la firma LETTA,
non intuita. La prima passata ha prodotto 5 TypeError su 6 chiamate, ed è una
lezione che va scritta nella mappa: `report_outcome(fact_id, *, good)`,
`source_trust_observe(*, confirmation=…, contradiction=…, outcome=…)`,
`_nascosti_per_eta(query, k, *, deep)`, `_trattenuti_safe(query)`.

Il pezzo che conta: `_retro_demote_source` promette di quarantinare i fatti già
scritti che citano una fonte diventata inaffidabile («the write-time gate only
stops FUTURE lies; the crossing re-evaluates the past ones»), e
`_rehabilitate_source` di restituire SOLO quelli. Si misura sui fatti, non sul
valore di ritorno (che è None per entrambe)."""
import os
import pathlib
import sys
import tempfile

WT = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(WT))
tmp = pathlib.Path(tempfile.mkdtemp(prefix="ws3-priv2-"))
os.environ["ENGRAM_DATA_DIR"] = str(tmp)
os.environ.pop("HIPPO_ENCODE_DELEGATE_ONLY", None)
from verimem import Memory  # noqa: E402

FONTE = "Verbale del 3 marzo: il canone del capannone 12 e' 5900 euro e la consegna e' del 3 marzo."
m = Memory(str(tmp / "p2.db"))
a = m.add("Il canone del capannone 12 e' 5900 euro.", source=FONTE, topic="p/a")
b = m.add("La consegna e' del 3 marzo.", source=FONTE, topic="p/b")
c = m.add("Il canone del capannone 12 e' 7300 euro.", source=FONTE, topic="p/c")
print("scritture:", a.get("status"), b.get("status"), c.get("status"))


def stati():
    return {i: (m.get(i) or {}).get("status") for i in (a.get("id"), b.get("id"), c.get("id"))}


print("stati:", stati())

print("\n=== firme LETTE (la prima passata aveva 5 TypeError su 6)")
try:
    print("  _trattenuti_safe(query):", str(m._trattenuti_safe("canone"))[:90])
except Exception as e:  # noqa: BLE001
    print("  _trattenuti_safe:", type(e).__name__, str(e)[:90])
try:
    print("  _nascosti_per_eta(query, k, deep=False):",
          str(m._nascosti_per_eta("canone", 5, deep=False))[:110])
except Exception as e:  # noqa: BLE001
    print("  _nascosti_per_eta:", type(e).__name__, str(e)[:90])
try:
    print("  report_outcome(fact_id, good=False):", m.report_outcome(a.get("id"), good=False))
except Exception as e:  # noqa: BLE001
    print("  report_outcome:", type(e).__name__, str(e)[:90])
print("  stati dopo report_outcome(good=False):", stati())
print("  trust della fonte dopo:", m.source_trust(FONTE))

print("\n=== IL PASSAGGIO: la fonte diventa inaffidabile e i fatti GIA' SCRITTI cadono?")
print("  trust prima:", m.source_trust(FONTE), "· stati:", stati())
m._retro_demote_source(FONTE)
print("  dopo _retro_demote_source  -> stati:", stati())
m._rehabilitate_source(FONTE)
print("  dopo _rehabilitate_source  -> stati:", stati())

print("\n=== source_trust_observe con gli argomenti nominati")
try:
    m.source_trust_observe(contradiction=FONTE)
    print("  observe(contradiction=fonte) · trust:", m.source_trust(FONTE))
    m.source_trust_observe(confirmation=[FONTE])
    print("  observe(confirmation=[fonte]) · trust:", m.source_trust(FONTE))
except Exception as e:  # noqa: BLE001
    print("  ECCEZIONE:", type(e).__name__, str(e)[:130])
