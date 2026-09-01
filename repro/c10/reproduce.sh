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

echo "== 0/5  la data dir e' isolata? (gli alias sono TRE, non uno)"
python - <<'PY'
import os
#: `verimem/_compat.py:168` — l'ordine E' la precedenza, verificato 02/09:
#:     _ALIAS_DATA_DIR = ("HIPPO_DATA_DIR", "ENGRAM_DATA_DIR", "VERIMEM_DATA_DIR")
#: Il banco pinna il PRIMO, quindi isola anche se gli altri due puntano allo
#: store reale. Ma se qualcuno ne esporta altri con valori DISCORDI il prodotto
#: avvisa su **stderr** — invisibile a chi redirige (segnalazione @ws8, 00:06).
#: Qui lo diciamo PRIMA, su stdout, che e' dove l'operatore guarda.
ALIAS = ("HIPPO_DATA_DIR", "ENGRAM_DATA_DIR", "VERIMEM_DATA_DIR")
messi = {a: os.environ[a] for a in ALIAS if os.environ.get(a)}
if not messi:
    print("   nessun alias esportato: il banco pinnera' il suo store temporaneo. OK")
elif len(set(messi.values())) == 1:
    print(f"   {len(messi)} alias, stesso valore: {next(iter(messi.values()))}. OK")
else:
    print("   ⚠️  ALIAS DISCORDI — il banco pinna HIPPO_DATA_DIR (che VINCE),")
    print("       ma se leggi i risultati con un altro strumento potresti guardare")
    print("       uno store diverso da quello su cui il banco ha scritto:")
    for a, v in messi.items():
        print(f"          {a} = {v}")
PY

echo "== 1/5  integrita' degli ingressi"
sha256sum -c repro/c10/MANIFEST.sha256

echo "== 2/5  il giudice locale c'e'?"
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

echo "== 3/5  esecuzione (~70 min, popolazione INTERA, nessun campionamento)"
python benchmark/c10_falsita_servite_vs_mem0.py \
    --popolazione truthfulqa --n 300 --out "$NUOVO"

echo "== 4/5  confronto con l'artefatto versionato"
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
