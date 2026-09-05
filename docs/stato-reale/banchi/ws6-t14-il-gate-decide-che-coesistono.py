"""T14 — il prodotto NON CERCA la contraddizione, o la cerca e non agisce?

    python docs/stato-reale/banchi/ws6-t14-il-livello-decide-se-il-prodotto-cerca.py

DUE BRACCI, UNA VARIABILE. Stessa fonte, stesso store, stessa coppia di
proposizioni; cambia SOLO `validate`.

LA CATENA CHE PORTA QUI (letta il 06/09, tutta statica):
  · `anti_confab_gate.py:2064`  `if level == "full": r = _l3_check(...)`
    e `_l3_check` e' l'unica via che alimenta `supersede_ids`.
  · `_resolve_level(None)` -> **'fast'** (eseguito)
  · `Memory.add(validate=)` ha default `None`; su MCP
    `_validate_kw = arguments.get("validate")`.
  · Nessuno dei due banchi che hanno prodotto T14 passa `validate`.
⇒ Con i default quel ramo non gira. Ma la QA/PO ha misurato che sull'SDK
l'`advice` di `validate_claim.py:885` — che sta DENTRO `_l3_check` — ARRIVA.
**Le due cose non possono essere entrambe vere**, e la misura incompleta puo'
benissimo essere la mia, che e' lettura statica. Questo banco esegue.

PREDIZIONE DEPOSITATA PRIMA (06/09 00:46):
  `validate=None`   -> nessun warning `L3`, nessuna supersessione
  `validate="full"` -> warning `L3` e il vecchio ritirato
COME MUORE: se anche con `full` non compare nulla, il difetto e' piu' in basso
e la catena non c'entra. Se compare in ENTRAMBI, il livello non e' la variabile
e la mia lettura statica ha un buco.

⚠️ CONTROLLO POSITIVO, senza il quale il banco non misura: la PRIMA scrittura
deve entrare e restare viva. Se il gate quarantinasse anche quella, l'assenza
di supersessione direbbe «non c'era niente da ritirare», non «non ha ritirato».

⛔ Store in tempdir, mai quello di casa. Carica il giudice: si prende lo slot.
"""
import os
import sys
import tempfile
import time

_tmp = tempfile.mkdtemp(prefix="ws6_t14_")
os.environ["HIPPO_DATA_DIR"] = _tmp
os.environ["ENGRAM_DATA_DIR"] = _tmp
os.environ.pop("VERIMEM_DATA_DIR", None)

_RADICE = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, _RADICE)

import verimem  # noqa: E402

print("verimem da:", verimem.__file__)
assert _RADICE.lower() in verimem.__file__.lower(), "albero sbagliato"

from verimem.client import Memory  # noqa: E402

FONTE_A = ("Il contratto con il fornitore di pagamenti indica Stripe come "
           "gestore del checkout per tutto il primo semestre.")
FONTE_B = ("La delibera di migrazione indica Adyen come nuovo gestore del "
           "checkout a partire dal secondo semestre.")
VECCHIO = "Il fornitore di pagamenti del servizio checkout e' Stripe."
NUOVO = "Il fornitore di pagamenti del servizio checkout e' Adyen."


def _giro(nome: str, validate):
    db = os.path.join(_tmp, f"{nome}.db")
    m = Memory(db)
    t0 = time.time()
    a = m.add(VECCHIO, topic="t14", source=FONTE_A, verified_by=["contratto"])
    vivo = m.semantic.get(a["id"]) if isinstance(a, dict) and a.get("id") else None
    # CONTROLLO POSITIVO: il primo fatto deve esserci e non essere quarantinato.
    stato_a = getattr(vivo, "status", None) if vivo is not None else "ASSENTE"
    b = m.add(NUOVO, topic="t14", source=FONTE_B, verified_by=["contratto"],
              validate=validate) if validate is not None else \
        m.add(NUOVO, topic="t14", source=FONTE_B, verified_by=["contratto"])
    dt = time.time() - t0
    chiavi = sorted(b) if isinstance(b, dict) else []
    warn = b.get("warnings") or b.get("anti_confab_warnings") or []
    layer = sorted({str(w.get("layer", "")) for w in warn if isinstance(w, dict)})
    dopo = m.semantic.get(a["id"]) if isinstance(a, dict) and a.get("id") else None
    sup = getattr(dopo, "superseded_by", None) if dopo is not None else None
    print(f"\n  ── validate={validate!r} ── ({dt:.1f}s)")
    print(f"     [cp] il primo fatto e' entrato con status  : {stato_a}")
    print(f"     layer dei warning sulla correzione         : {layer or 'NESSUNO'}")
    print(f"     un warning L3 c'e'?                        : "
          f"{any(l.startswith('L3') for l in layer)}")
    print(f"     il VECCHIO risulta superseded_by           : {sup!r}")
    print(f"     chiavi della ricevuta                      : {chiavi}")
    return {"stato_a": stato_a, "layer": layer, "superseded_by": sup}


print("\nT14 — IL LIVELLO DECIDE SE IL PRODOTTO CERCA?")
r_def = _giro("default", None)
r_full = _giro("full", "full")

print("\n  ── LETTURA ──")
if r_def["stato_a"] != "model_claim" and r_def["stato_a"] != "user_manual":
    print(f"  ⛔ CONTROLLO POSITIVO SPENTO: il primo fatto e' {r_def['stato_a']}.")
    print("     L'assenza di supersessione non prova niente. NON MISURATO.")
else:
    l3_def = any(x.startswith("L3") for x in r_def["layer"])
    l3_full = any(x.startswith("L3") for x in r_full["layer"])
    if not l3_def and l3_full:
        print("  ✅ PREDIZIONE CONFERMATA: col default L3 non gira, con `full` si'.")
        print("     T14 e' un DIFETTO DI DEFAULT — il prodotto non cerca, non")
        print("     e' che trova e tace.")
    elif l3_def and l3_full:
        print("  ❌ PREDIZIONE CADUTA: L3 gira in ENTRAMBI. Il livello non e' la")
        print("     variabile e la mia lettura statica ha un buco.")
    elif not l3_def and not l3_full:
        print("  ❌ PREDIZIONE CADUTA: L3 non gira NEMMENO con `full`. Il difetto")
        print("     e' piu' in basso.")
    else:
        print("  ⚠️ ESITO INATTESO: L3 col default e non con `full`. Da guardare.")


# ═══════════════════════════════════════════════════════════════════════════
# TERZO BRACCIO, aggiunto DOPO che i primi due hanno falsificato la predizione.
# Il layer non e' `L3` generico: e' **`L3-coexistence`**. Il prodotto trova la
# contraddizione e DECIDE che i due fatti coesistono — non «non cerca» e non
# «trova e tace».
# IPOTESI 5: coesistono perche' le due scritture hanno FONTI DIVERSE, e
# `_route_evolutions` chiede la «same canonical source». Con la STESSA fonte
# dovrebbe diventare un'evoluzione e ritirare il vecchio.
# COME MUORE: se anche con la stessa fonte resta `L3-coexistence`, la fonte non
# e' la variabile.
# ═══════════════════════════════════════════════════════════════════════════
print("\n\nTERZO BRACCIO — e se la fonte fosse LA STESSA?")


def _giro_stessa_fonte(nome: str, fonte_b: str, etichetta: str):
    db = os.path.join(_tmp, f"{nome}.db")
    m = Memory(db)
    a = m.add(VECCHIO, topic="t14", source=FONTE_A, verified_by=["contratto"])
    b = m.add(NUOVO, topic="t14", source=fonte_b, verified_by=["contratto"])
    warn = b.get("warnings") or [] if isinstance(b, dict) else []
    layer = sorted({str(w.get("layer", "")) for w in warn if isinstance(w, dict)})
    dopo = m.semantic.get(a["id"]) if isinstance(a, dict) and a.get("id") else None
    sup = getattr(dopo, "superseded_by", None) if dopo is not None else None
    print(f"\n  ── {etichetta} ──")
    print(f"     layer                        : {layer or 'NESSUNO'}")
    print(f"     il VECCHIO e' superseded_by  : {sup!r}")
    return layer, sup


l_div, s_div = _giro_stessa_fonte("fonti_diverse", FONTE_B, "fonti DIVERSE (come sopra)")
l_ug, s_ug = _giro_stessa_fonte("stessa_fonte", FONTE_A, "STESSA fonte")

print("\n  ── LETTURA DEL TERZO BRACCIO ──")
if s_ug and not s_div:
    print("  ✅ IPOTESI 5 CONFERMATA: con la stessa fonte il vecchio VIENE ritirato,")
    print("     con fonti diverse no. T14 e' la classificazione «coesistenza», e la")
    print("     variabile e' la FONTE, non il livello.")
elif l_ug == l_div:
    print("  ❌ IPOTESI 5 CADUTA: stesso esito con la stessa fonte. La fonte non e'")
    print("     la variabile; guardare le altre condizioni di _route_evolutions.")
else:
    print(f"  ⚠️ ESITO PARZIALE: diverse={l_div}/{s_div}  uguali={l_ug}/{s_ug}")
