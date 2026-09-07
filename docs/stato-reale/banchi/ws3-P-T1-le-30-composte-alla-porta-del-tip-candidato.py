"""P-T1 alla PORTA: le 30 composte su testo nuovo (banco non cieco del 07/09)
passano da run_validation_gate sul tip candidato (innesto + 3b-bis + morfologia
+ terzo stato), col giudice vero. Per ciascuna: action, layer sul claim caduto,
punteggi. Predizione P-T1 (design del terzo stato, depositata alle 13:30):
0 teste vere quarantinate (nessun L4-grounding), 17 scritture in review
(13 quarantena + 4 review del giudice sulla coda isolata), 13 ammesse con la
coda dentro (8 + 5 fuse). Argomento 1: il tip da cui importare verimem;
argomento 2: il file del banco con COMPOSTE."""
import importlib.util
import os
import pathlib
import sys
import time
from collections import Counter

WT = pathlib.Path(sys.argv[1]).resolve()
BANCO = pathlib.Path(sys.argv[2]).resolve()
sys.path.insert(0, str(WT))
os.environ.pop("HIPPO_ENCODE_DELEGATE_ONLY", None)
os.environ.pop("VERIMEM_CE_BAND_ENFORCE", None)
os.environ["ENGRAM_GROUNDING_BACKEND"] = "local"
import verimem  # noqa: E402

print("IMPORT DA", verimem.__file__)
from verimem.anti_confab_gate import run_validation_gate  # noqa: E402
from verimem.grounding_gate import (  # noqa: E402
    LOCAL_CE_MOAT_THRESHOLD,
    _ce_band_enforced,
    _ce_band_tau_hi,
)
from verimem.local_grounding import get_local_judge  # noqa: E402

spec = importlib.util.spec_from_file_location("banco", BANCO)
banco = importlib.util.module_from_spec(spec)
spec.loader.exec_module(banco)

t0 = time.perf_counter()
get_local_judge()._ensure_scorer()
print(f"warmup {time.perf_counter() - t0:.1f} s · moat {LOCAL_CE_MOAT_THRESHOLD} · tau_hi {_ce_band_tau_hi()} · banda {'ON' if _ce_band_enforced() else 'OFF'}")

esiti = Counter()
righe = []
for i in range(len(banco.COMPOSTE)):
    testa, fonte, _coda = banco.COMPOSTE[i]
    tutto = banco.composta(i)
    r = run_validation_gate(proposition=tutto, source=fonte, grounding_llm=None, ground_write=True,
                            verified_by=None, topic=None, agent=None)
    layers = sorted({str(w.get("layer")) for w in (r.warnings or [])})
    l4 = [ly for ly in layers if ly in ("L4-grounding", "L4-review", "L4-negazione", "L4-relazione")]
    cv = getattr(r, "claims_verdict", None) or []
    punteggi = [round(float(v["score"]), 1) if v.get("score") is not None else None for v in cv]
    caduto = [v.get("layer") for v in cv]
    if "L4-grounding" in layers:
        esito = "QUARANTENA"
    elif "L4-review" in layers:
        esito = "REVIEW"
    elif r.action == "persist":
        esito = "AMMESSA"
    else:
        esito = f"altro:{r.action}"
    esiti[esito] += 1
    righe.append((i, esito, r.action, len(getattr(r, "claims", []) or []), punteggi, caduto, l4))

print(f"\n30 composte alla porta del tip candidato: {dict(esiti)}")
print("P-T1: 0 QUARANTENA ->", "REGGE" if esiti["QUARANTENA"] == 0 else "FALSIFICATA",
      "· REVIEW 17 ->", "REGGE" if esiti["REVIEW"] == 17 else f"FALSIFICATA ({esiti['REVIEW']})",
      "· AMMESSA 13 ->", "REGGE" if esiti["AMMESSA"] == 13 else f"FALSIFICATA ({esiti['AMMESSA']})")
print(f"\n{'i':>2} {'esito':11s} {'action':10s} n  punteggi           layer per claim")
for i, esito, action, n, p, c, l4 in righe:
    print(f"{i:2d} {esito:11s} {action:10s} {n}  {str(p):18s} {c}  {l4}")
