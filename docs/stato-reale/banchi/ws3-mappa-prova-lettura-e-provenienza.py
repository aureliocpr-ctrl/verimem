"""Blocco 3 della mappa di client.py: le funzioni di LETTURA e di verdetto che
stanno dietro i claim del README sulla provenienza — count, explain,
esito_del_moat, chi_ha_quarantinato, trust_report, audit_log/audit_verify,
Risultati (il contenitore con sotto_il_pavimento e trattenuti).
Store temporaneo con path esplicito; quello di Aurelio non si tocca."""
import os
import pathlib
import sys
import tempfile

WT = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(WT))
tmp = pathlib.Path(tempfile.mkdtemp(prefix="ws3-mappa3-"))
os.environ["ENGRAM_DATA_DIR"] = str(tmp)
os.environ.pop("HIPPO_ENCODE_DELEGATE_ONLY", None)
from verimem import Memory  # noqa: E402

m = Memory(str(tmp / "m3.db"))
FONTE = "Verbale: il canone del capannone 12 e' 5900 euro e la consegna e' del 3 marzo."
r_ok = m.add("Il canone del capannone 12 e' 5900 euro.", source=FONTE, topic="mappa/lettura")
r_ko = m.add("Il canone del capannone 12 e' 7300 euro.", source=FONTE, topic="mappa/lettura")
print("SCRITTURE:", r_ok.get("status"), r_ok.get("id"), "|", r_ko.get("status"), r_ko.get("id"))

print("\n--- count()")
try:
    print("   ", m.count())
except Exception as e:  # noqa: BLE001
    print("   ECCEZIONE:", type(e).__name__, str(e)[:140])

print("\n--- explain(query)  [il claim della provenienza: perche' questo fatto]")
try:
    e = m.explain("canone del capannone 12")
    print("   tipo:", type(e).__name__, "· chiavi:", sorted(e)[:12] if isinstance(e, dict) else "-")
except Exception as ex:  # noqa: BLE001
    print("   ECCEZIONE:", type(ex).__name__, str(ex)[:140])

print("\n--- esito_del_moat(...) e chi_ha_quarantinato(...) sul fatto quarantinato")
try:
    from verimem.client import chi_ha_quarantinato, esito_del_moat
    fid = r_ko.get("id")
    riga = m.semantic.get(fid) if hasattr(m, "semantic") else None
    print("   esito_del_moat:", esito_del_moat(r_ko) if r_ko else None)
    print("   chi_ha_quarantinato:", chi_ha_quarantinato(riga) if riga is not None else "riga non letta")
except Exception as ex:  # noqa: BLE001
    print("   ECCEZIONE:", type(ex).__name__, str(ex)[:140])

print("\n--- trust_report()")
try:
    t = m.trust_report()
    print("   tipo:", type(t).__name__, "· chiavi:", sorted(t)[:10] if isinstance(t, dict) else "-")
except Exception as ex:  # noqa: BLE001
    print("   ECCEZIONE:", type(ex).__name__, str(ex)[:140])

print("\n--- audit_log() / audit_verify() / audit_head()")
for nome in ("audit_log", "audit_verify", "audit_head"):
    try:
        v = getattr(m, nome)()
        s = str(v)
        print(f"   {nome}: {type(v).__name__} {s[:90]}")
    except Exception as ex:  # noqa: BLE001
        print(f"   {nome}: ECCEZIONE {type(ex).__name__} {str(ex)[:110]}")

print("\n--- Risultati: sotto_il_pavimento e trattenuti sulla lettura")
try:
    hits = m.search("canone capannone", k=5)
    print("   tipo:", type(hits).__name__, "· len:", len(hits))
    for attr in ("sotto_il_pavimento", "trattenuti"):
        print(f"   {attr}:", getattr(hits, attr, "ASSENTE"))
except Exception as ex:  # noqa: BLE001
    print("   ECCEZIONE:", type(ex).__name__, str(ex)[:140])
