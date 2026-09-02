# -*- coding: utf-8 -*-
"""LA TRIPLA SU HALUEVAL — e come si prova un allineamento quando manca il valore
condiviso. Solo aritmetica sui punteggi gia' salvati: ZERO inferenza (ordine
carico-giu' del 02/09 21:14).

IL PROBLEMA. Su TruthfulQA l'allineamento era PROVATO: `giudice` di @ws3 e il mio
`score` sono lo stesso giudice sugli stessi claim e coincidevano 600/600. Su
HaluEval quel controllo non esiste, perche' io i punteggi del NOSTRO gate non li
ho. Restava un'assunzione: che @ws3 abbia iterato lo stesso file nello stesso
ordine, accodando a `pos` i claim veri e a `neg` i falsi.

DUE CONTROLLI AL POSTO DELLA PROVA MANCANTE:
  ① sui SUOI dati soltanto: applicando la soglia 40 ai suoi `giudice` devo
     ritrovare il suo `gate` dichiarato [0,19 · 0,55]. Se non torna, i suoi
     array non sono quelli che dice e mi fermo.
  ② IL TEST DI PERMUTAZIONE, che e' il pezzo che sostituisce la prova: se
     l'ordine assunto e' quello giusto, la tripla deve andare NETTAMENTE meglio
     che con uno dei tre punteggi mescolato a caso. Se va uguale, l'allineamento
     non porta informazione e il numero non vale — non e' una prova d'identita',
     ma e' falsificabile, ed e' piu' di «l'ho assunto».

🔮 PREDIZIONE, scritta prima (02/09 21:17): su HaluEval la tripla a media dei
   ranghi ferma fra il 58% e il 70% dei falsi a pari veri persi (il nostro gate:
   55,0%); e il test di permutazione deve dare un crollo di almeno 5 punti.
   FALSIFICATA se la tripla resta <= 55,0%, o se le permutazioni danno lo stesso
   risultato (allineamento inutile ⇒ numero non pubblicabile).
"""
import io
import json
import random

REPO = "C:/Users/aurel/Code/HippoAgent/"
S = ("C:/Users/aurel/AppData/Local/Temp/claude/"
     "C--Users-aurel-Desktop-ProgettiAI/"
     "78ba9444-dd97-498f-bd48-07ca991638a4/scratchpad/")

mio = [json.loads(x) for x in io.open(S + "factcg_halueval.jsonl", encoding="utf-8")
       if x.strip()]
w = json.load(io.open(REPO + "docs/stato-reale/banchi/_ws3_curva_scores.json",
                      encoding="utf-8"))["halueval-400"]

veri_k = [r for r in mio if r["label"] == 1]
falsi_k = [r for r in mio if r["label"] == 0]
print(f"  miei FactCG: veri {len(veri_k)} · falsi {len(falsi_k)}")
print(f"  di @ws3: giudice pos {len(w['giudice']['pos'])} neg {len(w['giudice']['neg'])}"
      f" · gate dichiarato {w['gate']}")

# ── CONTROLLO ① sui suoi dati soltanto ──────────────────────────────────
vp = sum(1 for x in w["giudice"]["pos"] if x < 40.0)
ff = sum(1 for x in w["giudice"]["neg"] if x < 40.0)
nv, nf = len(w["giudice"]["pos"]), len(w["giudice"]["neg"])
print(f"\n  CONTROLLO ① — soglia 40 sui suoi punteggi del giudice:")
print(f"    veri persi {vp}/{nv} = {vp/nv:.3f}  (dichiarato {w['gate'][0]})")
print(f"    falsi fermati {ff}/{nf} = {ff/nf:.3f}  (dichiarato {w['gate'][1]})")
ok1 = abs(vp / nv - w["gate"][0]) < 0.02 and abs(ff / nf - w["gate"][1]) < 0.02
print(f"    {'ACCESO' if ok1 else 'SPENTO — mi fermo'}")
if not ok1:
    raise SystemExit(1)

# ── costruisco i tre punteggi con l'ordine ASSUNTO ──────────────────────
def costruisci(perm=None, quale=None, seme=0):
    P = {}
    pos_g, neg_g = w["giudice"]["pos"], w["giudice"]["neg"]
    pos_m, neg_m = w["minicheck"]["pos"], w["minicheck"]["neg"]
    if perm:
        r = random.Random(seme)
        if quale == "mini":
            pos_m, neg_m = list(pos_m), list(neg_m)
            r.shuffle(pos_m)
            r.shuffle(neg_m)
        elif quale == "factcg":
            pass  # mescolato sotto, sui miei
    fp = [r_["p"][1] for r_ in veri_k]
    fn = [r_["p"][1] for r_ in falsi_k]
    if perm and quale == "factcg":
        r = random.Random(seme)
        fp, fn = list(fp), list(fn)
        r.shuffle(fp)
        r.shuffle(fn)
    for k in range(len(pos_g)):
        P[("v", k)] = {"nostro": pos_g[k] / 100.0, "mini": pos_m[k],
                       "factcg": fp[k], "label": 1}
    for k in range(len(neg_g)):
        P[("f", k)] = {"nostro": neg_g[k] / 100.0, "mini": neg_m[k],
                       "factcg": fn[k], "label": 0}
    return P


def tripla_ranghi(P):
    R = {}
    for c in ("nostro", "mini", "factcg"):
        o = sorted(P, key=lambda i: P[i][c])
        R[c] = {i: k / (len(o) - 1) for k, i in enumerate(o)}
    return lambda i: (R["nostro"][i] + R["mini"][i] + R["factcg"][i]) / 3.0


def iso(P, f, bersaglio):
    veri = [i for i in P if P[i]["label"] == 1]
    falsi = [i for i in P if P[i]["label"] == 0]
    o = sorted(veri, key=f)
    s = f(o[bersaglio - 1]) + 1e-12
    return sum(1 for i in falsi if f(i) < s)


P = costruisci()
BERS = vp                        # gli stessi veri persi del nostro gate: 38
base = 100 * ff / nf
t = 100 * iso(P, tripla_ranghi(P), BERS) / nf
print(f"\n  == LA TRIPLA A MEDIA DEI RANGHI su HaluEval, a pari veri persi ({BERS}) ==")
print(f"    il nostro gate da solo   {base:.1f}%")
print(f"    tripla a ranghi          {t:.1f}%      ({t - base:+.1f} punti)")

# ── CONTROLLO ② il test di permutazione ─────────────────────────────────
print("\n  CONTROLLO ② — e se l'ordine fosse sbagliato? (10 permutazioni per giudice)")
for quale in ("mini", "factcg"):
    val = [100 * iso(costruisci(True, quale, s), tripla_ranghi(costruisci(True, quale, s)),
                     BERS) / nf for s in range(10)]
    print(f"    con {quale:>6} mescolato: media {sum(val)/len(val):>5.1f}%"
          f"  min {min(val):>5.1f}%  max {max(val):>5.1f}%")
    if max(val) >= t:
        print("      ⛔ una permutazione fa uguale o meglio: l'ordine non porta"
              " informazione ⇒ il numero sopra NON e' pubblicabile")

print("\n  == I VERDETTI ==")
print(f"    predizione (58-70%): {'REGGE' if 58 <= t <= 70 else 'FALSIFICATA'}  ({t:.1f}%)")
print(f"    batte il nostro gate: {'SI' if t > base else 'NO'}")
