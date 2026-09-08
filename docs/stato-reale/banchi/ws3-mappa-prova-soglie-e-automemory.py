"""Blocco 7 della mappa di client.py: (a) i TRE DEBITI delle prove precedenti —
le funzioni che avevo chiamato male io — rifatti con la firma giusta; (b) le
funzioni di soglia, pure, misurabili senza store; (c) AutoMemory, che sta dietro
il claim README:280 «Opt-in auto-memory — AutoMemory(memory).observe(role, text)»."""
import os
import pathlib
import sys
import tempfile

WT = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(WT))
tmp = pathlib.Path(tempfile.mkdtemp(prefix="ws3-soglie-"))
os.environ["ENGRAM_DATA_DIR"] = str(tmp)
os.environ.pop("HIPPO_ENCODE_DELEGATE_ONLY", None)
from verimem import Memory  # noqa: E402
from verimem.client import (  # noqa: E402
    chi_ha_quarantinato,
    esito_del_moat,
    soglia_controllo_duplicati,
    soglia_fatto_lungo,
)

FONTE = "Verbale del 3 marzo: il canone del capannone 12 e' 5900 euro."
m = Memory(str(tmp / "s.db"))
ok = m.add("Il canone del capannone 12 e' 5900 euro.", source=FONTE, topic="s/ok")
ko = m.add("Il canone del capannone 12 e' 7300 euro.", source=FONTE, topic="s/ko")

print("=== (a) I TRE DEBITI, con la firma giusta")
for nome, r in (("ammesso", ok), ("quarantinato", ko)):
    w = r.get("warnings") or r.get("anti_confab_warnings") or []
    try:
        e = esito_del_moat(r, w, source=FONTE)
        print(f"  esito_del_moat({nome:12s}) -> {e!r}")
    except Exception as ex:  # noqa: BLE001
        print(f"  esito_del_moat({nome:12s}) -> ECCEZIONE {type(ex).__name__}: {str(ex)[:90]}")
try:
    print("  esito_del_moat(SENZA fonte)  ->", esito_del_moat(m.add("Nota libera.", topic="s/nf"), [], source=None))
except Exception as ex:  # noqa: BLE001
    print("  esito_del_moat(SENZA fonte)  -> ECCEZIONE", type(ex).__name__, str(ex)[:80])

for nome in ("source_trust", "consistency_trust"):
    try:
        v = getattr(m, nome)(FONTE)
        print(f"  {nome}(fonte) -> {v!r}")
    except Exception as ex:  # noqa: BLE001
        print(f"  {nome}(fonte) -> ECCEZIONE {type(ex).__name__}: {str(ex)[:90]}")

print("\n  chi_ha_quarantinato(riga del quarantinato):")
try:
    riga = m.get(ko.get("id"))
    print("   ->", chi_ha_quarantinato(riga))
except Exception as ex:  # noqa: BLE001
    print("   -> ECCEZIONE", type(ex).__name__, str(ex)[:110])

print("\n=== (b) le soglie, pure")
for nome, f in (("soglia_fatto_lungo", soglia_fatto_lungo),
                ("soglia_controllo_duplicati", soglia_controllo_duplicati)):
    try:
        print(f"  {nome}() -> {f()!r}")
    except Exception as ex:  # noqa: BLE001
        print(f"  {nome}() -> ECCEZIONE {type(ex).__name__}: {str(ex)[:80]}")

print("\n=== (c) AutoMemory  [README:280]")
try:
    from verimem import AutoMemory
    am = AutoMemory(m)
    print("  costruito:", type(am).__name__)
    r1 = am.observe("user", "Il capannone 12 costa 5900 euro al mese.")
    r2 = am.observe("assistant", "Va bene, me lo segno.")
    print("  observe(user, fatto)      ->", str(r1)[:120])
    print("  observe(assistant, chiac) ->", str(r2)[:120])
except Exception as ex:  # noqa: BLE001
    print("  ECCEZIONE:", type(ex).__name__, str(ex)[:160])
