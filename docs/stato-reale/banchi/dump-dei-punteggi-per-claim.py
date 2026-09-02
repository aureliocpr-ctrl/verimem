"""Anello ③ — dump dei grounding_score per claim, categoria e label.

UNA esecuzione che serve DUE ipotesi:
  · T1.2 (soglia per dominio): ottimizzare la soglia per strato richiede i
    punteggi per categoria, che nessun banco salva.
  · T1.4 (terzo stato + split-conformal): la mia predizione — «>=60% dei veri
    persi dal moat ha grounding fra 20 e 40» — si misura sugli stessi punteggi.

Non decide niente: SCRIVE. Le due ipotesi si valutano poi offline, senza altri
carichi del giudice.

LA CHIAMATA E' COPIATA dal banco della baseline, non riscritta a memoria: per
NOME e non posizionale, e l'esito si legge da `res.action != "persist"`, non da
uno `status`. Riscriverla a memoria e' costato due esecuzioni a vuoto.

PREFLIGHT (W7-87): in un processo nuovo il moat parte «warming» e il gate
AMMETTE TUTTO. Qui si attende judge_state()=='ready' e lo si dichiara.

DUE CONTROLLI CHE DEVONO ACCENDERSI, o il dump non si usa:
  · sui 300 falsi il gate deve fermarne >= 200 (baseline: 260 = 86,7%)
  · i claim SENZA grounding_score devono essere pochi: se il campo non c'e',
    il dump e' inutile anche col conteggio giusto.
"""
import io
import json
import os
import sys
import time

os.environ.setdefault("VERIMEM_HOSTED", "1")

P = "benchmark/data/external/truthfulqa_pairs_heldout.jsonl"
OUT = "punteggi_heldout.jsonl"
NL = chr(10)

from verimem.local_grounding import judge_state, warm_local_judge_async  # noqa: E402

print(f"  judge_state iniziale: {judge_state()}")
warm_local_judge_async()
t0 = time.time()
while judge_state() != "ready" and time.time() - t0 < 180:
    time.sleep(1.0)
print(f"  judge_state dopo warmup: {judge_state()}  ({time.time() - t0:.1f}s)")
if judge_state() != "ready":
    print("  CONTROLLO SPENTO: il giudice non e' ready, il dump NON va usato")
    sys.exit(1)

from verimem.anti_confab_gate import run_validation_gate  # noqa: E402

righe = [json.loads(x) for x in io.open(P, encoding="utf-8") if x.strip()]
print(f"  righe: {len(righe)}  ->  {OUT}")

out = io.open(OUT, "w", encoding="utf-8")
fermati_veri = fermati_falsi = senza_score = 0
t0 = time.time()
for i, r in enumerate(righe, 1):
    claim, src = r.get("claim", ""), r.get("source", "")
    try:
        res = run_validation_gate(
            proposition=claim, verified_by=None,
            topic="banco/dump-punteggi", agent=None,
            source=src, ground_write=True)
    except Exception as exc:  # noqa: BLE001
        out.write(json.dumps({"i": i, "errore": str(exc)[:120]}) + NL)
        continue
    layers = sorted({w.get("layer") for w in (res.warnings or [])
                     if isinstance(w, dict) and w.get("layer")})
    fermato = res.action != "persist"
    score = getattr(res, "grounding_score", None)
    if score is None:
        senza_score += 1
    if r.get("label") == 1 and fermato:
        fermati_veri += 1
    if r.get("label") == 0 and fermato:
        fermati_falsi += 1
    riga = {
        "i": i, "label": r.get("label"), "category": r.get("category"),
        "kind": r.get("kind"), "score": score, "fermato": fermato,
        "action": res.action, "layers": layers, "len_claim": len(claim),
    }
    out.write(json.dumps(riga, ensure_ascii=False) + NL)
    if i % 100 == 0:
        print(f"    ...{i}/{len(righe)}  ({time.time() - t0:.0f}s)")
out.close()

veri = sum(1 for r in righe if r.get("label") == 1)
falsi = sum(1 for r in righe if r.get("label") == 0)
print()
print(f"  claim senza grounding_score: {senza_score}/{len(righe)}")
print(f"  VERI fermati  {fermati_veri}/{veri}   ({100 * fermati_veri / veri:.1f}%)")
print(f"  FALSI fermati {fermati_falsi}/{falsi}   ({100 * fermati_falsi / falsi:.1f}%)")
if fermati_falsi < 200:
    print("  CONTROLLO 1 SPENTO: falsi fermati troppo pochi => dump NON usabile")
    sys.exit(1)
if senza_score > len(righe) // 10:
    print("  CONTROLLO 2 SPENTO: troppi claim senza punteggio => dump NON usabile")
    sys.exit(1)
print("  DUE CONTROLLI ACCESI: il gate ha giudicato e i punteggi ci sono")
sys.exit(0)
