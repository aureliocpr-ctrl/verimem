# -*- coding: utf-8 -*-
"""LA TRIPLA SU HALUEVAL, con l'allineamento PROVATO invece che assunto.

Alle 21:18 avevo provato a fare questo con i punteggi `pos`/`neg` di @ws3 e il
test di permutazione l'aveva SPENTO: mescolando a caso si otteneva di piu'
(65,8% contro 62,5%), quindi l'ordine assunto non portava informazione (W7-129).
Mancava il pezzo che nessun ragionamento poteva sostituire: **i punteggi del
NOSTRO giudice nel MIO ordine di riga**. Ora ci sono — rieseguiti sui 400 con lo
slot 2, `giudice_halueval.jsonl`.

E servono a DUE cose, non a una:
  ① sono il terzo punteggio della tripla;
  ② 🔑 PROVANO O FALSIFICANO L'ALLINEAMENTO DI @ws3, che finora era
     un'assunzione. Il suo `giudice['pos']` e il mio `score` filtrato sui veri
     sono LO STESSO giudice sugli STESSI claim: se coincidono, il suo ordine e'
     quello che pensavo e MiniCheck si puo' usare; se non coincidono, il suo
     ordine e' diverso e la tripla su questo corpus resta non misurabile.
     E' lo stesso controllo che su TruthfulQA aveva dato 600/600.

🔮 PREDIZIONE, scritta PRIMA (02/09 22:38):
  ① l'allineamento si prova: >= 390/400 valori identici entro 0,01
  ② se si prova, la tripla a media dei ranghi a pari veri persi (19,0%) ferma
     fra il 55% e il 70% dei falsi (il gate intero: 55,0%)
  ③ e il test di permutazione stavolta si ACCENDE: mescolare deve PEGGIORARE
  ④ FALSIFICATA se l'allineamento non si prova, o se la tripla resta <= 55,0%,
     o se mescolando si ottiene ancora di piu'.
"""
import io
import json
import os
import random

REPO = "C:/Users/aurel/Code/HippoAgent/"
S = ("C:/Users/aurel/AppData/Local/Temp/claude/"
     "C--Users-aurel-Desktop-ProgettiAI/"
     "78ba9444-dd97-498f-bd48-07ca991638a4/scratchpad/")

mio_g = {json.loads(x)["i"]: json.loads(x)
         for x in io.open(S + "giudice_halueval.jsonl", encoding="utf-8") if x.strip()}
mio_f = {json.loads(x)["i"]: json.loads(x)
         for x in io.open(S + "factcg_halueval.jsonl", encoding="utf-8") if x.strip()}
w = json.load(io.open(REPO + "docs/stato-reale/banchi/_ws3_curva_scores.json",
                      encoding="utf-8"))["halueval-400"]

ordine = sorted(mio_g)
veri = [i for i in ordine if mio_g[i]["label"] == 1]
falsi = [i for i in ordine if mio_g[i]["label"] == 0]
print(f"  miei: {len(mio_g)} claim ({len(veri)} veri · {len(falsi)} falsi)")

# ── ① LA PROVA DELL'ALLINEAMENTO ────────────────────────────────────────
mie_p = [mio_g[i].get("score") or 0.0 for i in veri]
mie_n = [mio_g[i].get("score") or 0.0 for i in falsi]
ug = (sum(1 for a, b in zip(mie_p, w["giudice"]["pos"]) if abs(a - b) < 0.01)
      + sum(1 for a, b in zip(mie_n, w["giudice"]["neg"]) if abs(a - b) < 0.01))
print(f"\n  ① ALLINEAMENTO: {ug}/400 valori del giudice identici entro 0,01")
print(f"     {'PROVATO' if ug >= 390 else 'NON PROVATO — MiniCheck non e usabile qui'}")
print(f"     primi 3 miei: {[round(x, 2) for x in mie_p[:3]]}")
print(f"     primi 3 suoi: {[round(x, 2) for x in w['giudice']['pos'][:3]]}")
if ug < 390:
    print("\n  ⇒ mi fermo: senza l'allineamento la tripla su HaluEval non e'"
          " misurabile, e il numero di W7-129 resta l'ultimo detto.")
    raise SystemExit(0)

# ── i tre punteggi, tutti 0-1, nel MIO ordine ───────────────────────────
P = {}
for k, i in enumerate(veri):
    P[i] = {"nostro": (mio_g[i].get("score") or 0.0) / 100.0,
            "mini": w["minicheck"]["pos"][k], "factcg": mio_f[i]["p"][1], "label": 1}
for k, i in enumerate(falsi):
    P[i] = {"nostro": (mio_g[i].get("score") or 0.0) / 100.0,
            "mini": w["minicheck"]["neg"][k], "factcg": mio_f[i]["p"][1], "label": 0}


def ranghi(campo, tab):
    o = sorted(tab, key=lambda i: tab[i][campo])
    return {i: k / (len(o) - 1) for k, i in enumerate(o)}


def valuta(tab, f, bersaglio):
    v = [i for i in tab if tab[i]["label"] == 1]
    fa = [i for i in tab if tab[i]["label"] == 0]
    o = sorted(v, key=f)
    s = f(o[bersaglio - 1]) + 1e-12
    return 100 * sum(1 for i in fa if f(i) < s) / len(fa)


BERS = 38            # 19,0% dei 200 veri: i veri persi del gate intero
BASE = 55.0          # i falsi fermati dal gate intero (@ws7)
R = {c: ranghi(c, P) for c in ("nostro", "mini", "factcg")}
tri = lambda i: (R["nostro"][i] + R["mini"][i] + R["factcg"][i]) / 3.0
med = lambda i: (P[i]["nostro"] + P[i]["mini"] + P[i]["factcg"]) / 3.0
solo = lambda i: P[i]["nostro"]

print(f"\n  ② A PARI VERI PERSI ({BERS}/200 = 19,0%)")
for nome, f in (("il moat da solo", solo), ("tripla · media", med),
                ("tripla · ranghi", tri)):
    print(f"     {nome:<22} {valuta(P, f, BERS):>5.1f}%")
print(f"     {'il GATE INTERO (@ws7)':<22} {BASE:>5.1f}%")
t = valuta(P, tri, BERS)

# ── ③ IL TEST DI PERMUTAZIONE, che stavolta deve ACCENDERSI ─────────────
print("\n  ③ E SE L'ORDINE FOSSE SBAGLIATO? (10 permutazioni per giudice)")
acceso = True
for quale in ("mini", "factcg"):
    vals = []
    for sd in range(10):
        rng = random.Random(sd)
        Q = {i: dict(P[i]) for i in P}
        vv = [i for i in Q if Q[i]["label"] == 1]
        ff = [i for i in Q if Q[i]["label"] == 0]
        for gruppo in (vv, ff):
            val = [Q[i][quale] for i in gruppo]
            rng.shuffle(val)
            for i, x in zip(gruppo, val):
                Q[i][quale] = x
        RQ = {c: ranghi(c, Q) for c in ("nostro", "mini", "factcg")}
        vals.append(valuta(Q, lambda i: (RQ["nostro"][i] + RQ["mini"][i]
                                         + RQ["factcg"][i]) / 3.0, BERS))
    peggiora = max(vals) < t
    acceso &= peggiora
    print(f"     con {quale:>6} mescolato: media {sum(vals)/10:>5.1f}%"
          f" · max {max(vals):>5.1f}%   {'ACCESO' if peggiora else 'SPENTO'}")

print("\n  == I VERDETTI, col controllo dentro ==")
if not acceso:
    print("     NON PUBBLICABILE: mescolando si ottiene ancora uguale o meglio.")
else:
    print(f"     predizione (55-70%): {'REGGE' if 55 <= t <= 70 else 'FALSIFICATA'}"
          f"  ({t:.1f}%)")
    print(f"     batte il gate intero: {'SI' if t > BASE else 'NO'}"
          f"   ({t:.1f}% contro {BASE:.1f}%)")
