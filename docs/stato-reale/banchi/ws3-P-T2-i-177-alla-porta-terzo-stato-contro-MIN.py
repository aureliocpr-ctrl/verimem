"""P-T2: i 177 «veri composti che cambiano verdetto» di P-A passano dalla PORTA
del tip candidato (innesto + 3b-bis + morfologia + terzo stato), col giudice
vero e lo span come fonte. Predizione depositata il 07/09 nel design del terzo
stato: tutti verso REVIEW, 0 verso QUARANTENA. Muore se anche uno finisce in
quarantena per il moat (L4-grounding) quando l'intero passa la banda.

Il confronto è con lo stesso identico passaggio sull'albero SENZA terzo stato
(argomento 2): stessa fonte, stesso giudice, una variabile sola.
Argomenti: <wt_tip> [<wt_senza>]
"""
import json
import os
import pathlib
import sys
import time
from collections import Counter


def esito(r) -> str:
    layers = {str(w.get("layer")) for w in (r.warnings or [])}
    if "L4-grounding" in layers or "L4.1" in layers:
        return "QUARANTENA"
    if "L4-review" in layers:
        return "REVIEW"
    if r.action == "persist":
        return "AMMESSA"
    return f"altro:{r.action}"


def gira(wt: str, det: list, etichetta: str) -> tuple[Counter, dict]:
    for k in list(sys.modules):
        if k == "verimem" or k.startswith("verimem."):
            del sys.modules[k]
    sys.path.insert(0, wt)
    import verimem
    print(f"\n[{etichetta}] IMPORT DA {verimem.__file__}")
    from verimem.anti_confab_gate import run_validation_gate
    from verimem.local_grounding import get_local_judge
    t0 = time.perf_counter()
    get_local_judge()._ensure_scorer()
    print(f"[{etichetta}] warmup {time.perf_counter() - t0:.1f} s")
    conti, per_id = Counter(), {}
    t0 = time.perf_counter()
    for d in det:
        r = run_validation_gate(proposition=d["prop"], source=d["span"] or "", grounding_llm=None,
                                ground_write=True, verified_by=None, topic=None, agent=None)
        e = esito(r)
        conti[e] += 1
        per_id[d["id"][:12]] = e
    print(f"[{etichetta}] {len(det)} record in {time.perf_counter() - t0:.0f} s: {dict(conti)}")
    sys.path.remove(wt)
    return conti, per_id


QUI = pathlib.Path(__file__).resolve().parent  # docs/stato-reale/banchi
os.environ.pop("HIPPO_ENCODE_DELEGATE_ONLY", None)
os.environ.pop("VERIMEM_CE_BAND_ENFORCE", None)
os.environ["ENGRAM_GROUNDING_BACKEND"] = "local"
det = json.load(open(QUI / "ws3-P-A-i-177-veri-composti-che-cambiano-verdetto.json", encoding="utf-8"))
c_tip, id_tip = gira(sys.argv[1], det, "TIP con terzo stato")
if len(sys.argv) > 2:
    c_no, id_no = gira(sys.argv[2], det, "SENZA terzo stato")
    print("\nSPOSTAMENTI (senza -> con il terzo stato):")
    mosse = Counter((id_no[k], id_tip[k]) for k in id_tip)
    for (a, b), n in mosse.most_common():
        print(f"  {a:12s} -> {b:12s} {n}")
_q = c_tip["QUARANTENA"]
print("\nP-T2 (0 QUARANTENA sul tip): " + ("REGGE" if _q == 0 else f"FALSIFICATA ({_q})"))
