#!/usr/bin/env bash
# Riproduce il C10 — «che tasso di falsita' serviamo» — e DICE DA SOLO se torna.
#
# Non stampa numeri da interpretare: confronta il run nuovo con l'artefatto
# versionato campo per campo ed esce 0 solo se coincidono entro tolleranza.
# I valori attesi NON sono scritti qui: si leggono da
# `benchmark/results/c10_heldout_intero.json`, che e' sotto hash nel MANIFEST.
# Cosi' chi cambia il numero deve cambiare l'artefatto, e il MANIFEST se ne
# accorge.
set -euo pipefail

RADICE="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$RADICE"
ATTESO="benchmark/results/c10_heldout_intero.json"
NUOVO="${OUT:-/tmp/c10_riprodotto.json}"
TOLL="${TOLL:-1.0}"   # punti percentuali di scarto ammessi

echo "== 1/4  integrita' degli ingressi"
sha256sum -c repro/c10/MANIFEST.sha256

echo "== 2/4  il giudice locale c'e'?"
if ! python - <<'PY'
import sys
try:
    #: `_resolve_model_dir` e' privata ma e' l'UNICA che applica il fallback
    #: reale: env `ENGRAM_LOCAL_GATE_MODEL` -> default (~/.cache/verimem/...)
    #: -> legacy (~/.engram/models/...). Guardare solo DEFAULT_MODEL_DIR e'
    #: un FALSO ALLARME per chiunque abbia gia' usato verimem prima del
    #: cambio di percorso: la mia macchina, il 02/09, aveva il modello in
    #: legacy e il primo controllo diceva «ASSENTE» con il gate funzionante.
    from verimem.local_grounding import _resolve_model_dir, holds_the_weights
except Exception as e:                      # noqa: BLE001
    print(f"   verimem non importabile: {e}"); sys.exit(1)
d = _resolve_model_dir(None)
ok = holds_the_weights(d)
print(f"   {d} -> {'presente' if ok else 'ASSENTE'}")
sys.exit(0 if ok else 2)
PY
then
    echo "   ⚠️  manca il modello del moat (~746 MB). Scaricalo con \`verimem warmup\`"
    echo "      e rilancia: SENZA di esso il gate parte in 'warming' e AMMETTE TUTTO,"
    echo "      producendo numeri puliti e privi di significato (registro: W7-87)."
    exit 3
fi

echo "== 3/4  esecuzione (~70 min, popolazione INTERA, nessun campionamento)"
python benchmark/c10_falsita_servite_vs_mem0.py \
    --popolazione truthfulqa --n 300 --out "$NUOVO"

echo "== 4/4  confronto con l'artefatto versionato"
python - "$ATTESO" "$NUOVO" "$TOLL" <<'PY'
import json, sys
atteso, nuovo, toll = json.load(open(sys.argv[1])), json.load(open(sys.argv[2])), float(sys.argv[3])

#: i campi che DEVONO coincidere esattamente (identita' del banco)
UGUALI = ["popolazione"]
#: i campi numerici, confrontati entro tolleranza in punti
NUMERI = ["falsi_ammessi", "falsi_fra_i_serviti", "criterio_cieco_pct",
          "serviti", "falsi_totali", "saltati", "moat_esclusivo",
          "moat_con_layer_lessicale"]

righe, rotto = [], False
for k in UGUALI:
    a, n = atteso.get(k), nuovo.get(k)
    ok = a == n
    rotto |= not ok
    righe.append(f"   {'OK ' if ok else 'DIV'}  {k:<26} atteso={a!r}  nuovo={n!r}")
for k in NUMERI:
    a, n = atteso.get(k), nuovo.get(k)
    if a is None or n is None:
        righe.append(f"   --   {k:<26} assente in uno dei due (atteso={a}, nuovo={n})")
        continue
    if isinstance(a, (int, float)) and isinstance(n, (int, float)):
        ok = abs(a - n) <= toll
        rotto |= not ok
        righe.append(f"   {'OK ' if ok else 'DIV'}  {k:<26} atteso={a}  nuovo={n}  Δ={n - a:+.3f}")
    else:
        ok = a == n
        rotto |= not ok
        righe.append(f"   {'OK ' if ok else 'DIV'}  {k:<26} atteso={a!r}  nuovo={n!r}")

print("\n".join(righe))
print(f"\n   commit dell'artefatto: {atteso.get('commit')}   ·   del run: {nuovo.get('commit')}")
if atteso.get("commit") != nuovo.get("commit"):
    print("   ⚠️  commit DIVERSI: uno scarto qui non e' un difetto, e' un'altra versione.")
print("\n" + ("🔴 NON RIPRODOTTO — vedi le righe DIV sopra" if rotto
              else f"✅ RIPRODOTTO entro {toll} punti"))
sys.exit(1 if rotto else 0)
PY
