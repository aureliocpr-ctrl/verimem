# -*- coding: utf-8 -*-
"""IL GIUDICE SUI 400 DI HALUEVAL, indicizzato per riga — pronto, da lanciare
quando si libera uno slot di inferenza (disciplina del 02/09 21:40).

PERCHE' SERVE. La tripla a media dei ranghi e' misurata solo su TruthfulQA
(`W7-128`: 90,7% dei falsi a pari veri, 25,3% di veri persi a pari falsi). Su
HaluEval non l'ho potuta misurare perche' l'allineamento fra i punteggi di @ws3
(`pos`/`neg` separati) e i miei di FactCG (indicizzati per riga) NON e'
dimostrabile — e il test di permutazione l'ha spento: mescolando a caso si
otteneva DI PIU' (65,8% contro 62,5%), cioe' l'ordine assunto non portava
informazione (`W7-129`).

LA CURA NON E' CHIEDERE IL SUO FILE: e' rieseguire IO il giudice sui 400 nello
STESSO ordine di riga dei miei punteggi FactCG. Cosi' l'allineamento non e'
assunto ne' concordato: e' MIO PER COSTRUZIONE, e verificabile.

CONTROLLI CHE DEVONO ACCENDERSI, in quest'ordine:
  ① PREFLIGHT DEL MOAT (W7-87): in un processo nuovo `judge_state()` parte
     `warming` e il gate AMMETTE TUTTO — sarebbero 0 fermati su 400 e il banco
     misurerebbe il nulla. Si aspetta `ready` PRIMA di cominciare e si stampa lo
     stato. `judge_state` sta in `verimem.local_grounding`, NON in
     `verimem.grounding_gate`.
  ② RIPRODUZIONE DEI NUMERI NOTI: a soglia 40 il moat da solo deve dare circa
     8,0% di veri persi e 45,5% di falsi fermati — i valori che ho ricavato dai
     punteggi di @ws3 (`W7-129`). Se non li riproduco, o il mio dump e' sbagliato
     o i suoi lo erano: in entrambi i casi mi fermo e lo dico.

🔮 PREDIZIONE, scritta PRIMA (02/09 21:55):
  · riprodurro' i numeri di @ws3 entro 2 punti (8,0% e 45,5%)
  · e la tripla su HaluEval, a pari veri persi del gate (19,0%), fermera' fra il
    56% e il 68% dei falsi — cioe' MEGLIO del 55,0% del gate ma MENO del salto
    visto su TruthfulQA (+4,0 punti), perche' li' il nostro giudice e' il piu'
    forte dei tre mentre qui e' molto piu' debole (45,5% da solo).
  · FALSIFICATA se la tripla resta <= 55,0%, oppure se non riproduco i numeri.
"""
import io
import json
import os
import time

os.environ.setdefault("VERIMEM_AGENT", "Paragone")

DATI = ("C:/Users/aurel/AppData/Local/Temp/claude/"
        "C--Users-aurel-Desktop-ProgettiAI/"
        "c062024e-cc77-4fac-ba67-fb1db54449b6/scratchpad/"
        "halueval_come_truthfulqa.jsonl")
OUT = ("C:/Users/aurel/AppData/Local/Temp/claude/"
       "C--Users-aurel-Desktop-ProgettiAI/"
       "78ba9444-dd97-498f-bd48-07ca991638a4/scratchpad/"
       "giudice_halueval.jsonl")

from verimem.local_grounding import judge_state, warm_local_judge_async  # noqa: E402

print("  ① PREFLIGHT DEL MOAT")
warm_local_judge_async()
t0 = time.time()
while judge_state() != "ready" and time.time() - t0 < 300:
    time.sleep(2)
stato = judge_state()
print(f"    judge_state() = {stato} dopo {time.time() - t0:.1f}s")
if stato != "ready":
    print("    CONTROLLO SPENTO: il giudice non e' pronto, il gate ammetterebbe tutto")
    raise SystemExit(1)

from verimem.anti_confab_gate import run_validation_gate  # noqa: E402

righe = [json.loads(x) for x in io.open(DATI, encoding="utf-8") if x.strip()]
print(f"\n  {len(righe)} claim, nell'ordine di riga del file (lo stesso dei miei FactCG)")

t0 = time.time()
out = io.open(OUT, "w", encoding="utf-8")
for i, r in enumerate(righe, 1):
    res = run_validation_gate(
        proposition=r["claim"], verified_by=None,
        topic="banco/giudice-halueval", agent=None,
        source=r["source"], ground_write=True)
    layers = sorted({w.get("layer") for w in (res.warnings or [])
                     if isinstance(w, dict) and w.get("layer")})
    out.write(json.dumps({
        "i": i, "label": r["label"],
        "score": getattr(res, "grounding_score", None),
        "fermato": res.action != "persist", "layers": layers}) + chr(10))
    if i % 100 == 0:
        print(f"    ...{i}/{len(righe)}  ({time.time() - t0:.0f}s)", flush=True)
out.close()
print(f"  fatto in {time.time() - t0:.0f}s -> {OUT}")

d = [json.loads(x) for x in io.open(OUT, encoding="utf-8") if x.strip()]
veri = [r for r in d if r["label"] == 1]
falsi = [r for r in d if r["label"] == 0]
senza = sum(1 for r in d if r["score"] is None)
print(f"\n  ② RIPRODUCO I NUMERI NOTI?  (claim senza grounding_score: {senza})")
vp = sum(1 for r in veri if (r["score"] or 0) < 40)
ff = sum(1 for r in falsi if (r["score"] or 0) < 40)
pv, pf = 100 * vp / len(veri), 100 * ff / len(falsi)
print(f"    moat da solo a soglia 40: veri persi {vp}/{len(veri)} = {pv:.1f}%"
      f"  (atteso ~8,0%)")
print(f"                              falsi fermati {ff}/{len(falsi)} = {pf:.1f}%"
      f"  (atteso ~45,5%)")
ok = abs(pv - 8.0) <= 2.0 and abs(pf - 45.5) <= 2.0
print(f"    {'ACCESO: riproduco @ws3' if ok else 'SPENTO: NON riproduco — mi fermo e lo dico'}")
vpg = sum(1 for r in veri if r["fermato"])
ffg = sum(1 for r in falsi if r["fermato"])
print(f"    e il GATE INTERO: veri persi {100*vpg/len(veri):.1f}% (atteso 19,0%)"
      f" · falsi fermati {100*ffg/len(falsi):.1f}% (atteso 55,0%)")
