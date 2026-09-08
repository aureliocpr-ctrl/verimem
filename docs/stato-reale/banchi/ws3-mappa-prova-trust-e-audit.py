"""Blocco 6 della mappa di client.py: il blocco TRUST e AUDIT — le funzioni che
il prodotto usa per dire «di questa fonte mi fido meno» e per lasciare una
traccia verificabile. Sono 15 voci contigue (2394-2743) e stanno dietro i claim
di provenienza.

Qui l'audit si accende davvero (VERIMEM_AUDIT_LOG=1) invece di guardarlo spento
come nel blocco precedente: senza la variabile la traccia non esiste, e una
mappa che si ferma lì non dice se funziona."""
import os
import pathlib
import sys
import tempfile

WT = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(WT))
tmp = pathlib.Path(tempfile.mkdtemp(prefix="ws3-trust-"))
os.environ["ENGRAM_DATA_DIR"] = str(tmp)
os.environ["VERIMEM_AUDIT_LOG"] = "1"          # <- l'opt-in dichiarato nel docstring
os.environ.pop("HIPPO_ENCODE_DELEGATE_ONLY", None)
from verimem import Memory  # noqa: E402

FONTE = "Verbale del 3 marzo: il canone del capannone 12 e' 5900 euro."
m = Memory(str(tmp / "t.db"))
ok = m.add("Il canone del capannone 12 e' 5900 euro.", source=FONTE, topic="t/ok")
ko = m.add("Il canone del capannone 12 e' 7300 euro.", source=FONTE, topic="t/ko")
print("scritture:", ok.get("status"), "|", ko.get("status"))

print("\n--- audit_log() CON VERIMEM_AUDIT_LOG=1")
try:
    log = m.audit_log()
    print("   righe:", len(log))
    for r in log[:2]:
        print("   campi:", sorted(r)[:12])
        print("   disposition:", r.get("disposition"), "· topic:", r.get("topic"))
except Exception as e:  # noqa: BLE001
    print("   ECCEZIONE:", type(e).__name__, str(e)[:140])

print("\n--- audit_log(disposition='quarantined')  [il filtro dichiarato]")
try:
    q = m.audit_log(disposition="quarantined")
    print("   righe:", len(q), "· dispositions:", [r.get("disposition") for r in q])
except Exception as e:  # noqa: BLE001
    print("   ECCEZIONE:", type(e).__name__, str(e)[:140])

print("\n--- audit_verify() / audit_head(): la catena e' verificabile?")
for nome in ("audit_verify", "audit_head", "audit_head_signed"):
    try:
        v = getattr(m, nome)()
        print(f"   {nome}: {type(v).__name__} {str(v)[:120]}")
    except Exception as e:  # noqa: BLE001
        print(f"   {nome}: ECCEZIONE {type(e).__name__} {str(e)[:110]}")

print("\n--- source_trust / consistency_trust / trust_report(query)")
for nome, args in (("source_trust", ()), ("consistency_trust", ()),
                   ("trust_report", ("canone capannone",))):
    try:
        v = getattr(m, nome)(*args)
        s = str(v)
        print(f"   {nome}{args}: {type(v).__name__} {s[:150]}")
    except Exception as e:  # noqa: BLE001
        print(f"   {nome}{args}: ECCEZIONE {type(e).__name__} {str(e)[:110]}")

print("\n--- report_outcome / record_decision / why_decision (il ciclo delle decisioni)")
try:
    d = m.record_decision("uso Postgres per l'analytics", topic="t/dec")
    print("   record_decision ->", str(d)[:110])
    print("   why_decision    ->", str(m.why_decision(d.get("id") if isinstance(d, dict) else d))[:110])
except Exception as e:  # noqa: BLE001
    print("   ECCEZIONE:", type(e).__name__, str(e)[:140])
