# -*- coding: utf-8 -*-
"""LA CASCATA — l'ipotesi che ho scritto come APERTA in W7-127, misurata subito.

In W7-127 ho dichiarato: «non ho provato una regola che consulti il secondo
giudice SOLO sotto una soglia nostra, che e' l'unica forma che potrebbe
recuperare i 61 senza pagare sui falsi — e' un'ipotesi, non un risultato».
Un'ipotesi dichiarata aperta che si puo' chiudere in due minuti coi dati gia' in
casa va chiusa: un limite dichiarato e' un debito, e lo paga chi legge.

LA REGOLA: se il NOSTRO punteggio e' sotto una soglia bassa S, decide FactCG;
sopra, decidiamo noi. Cosi' il secondo giudice tocca SOLO i casi che stiamo gia'
buttando, e non puo' rovinare quelli che trattiamo bene.

🔮 PREDIZIONE, scritta PRIMA di eseguire (02/09 21:04):
  · la cascata recupera fra 15 e 40 dei 61 veri sul fondo
  · ma paga: a pari veri persi (88/300) i falsi fermati SCENDONO sotto l'86,7%
  · FALSIFICATA se i falsi fermati restano >= 86,7% recuperando >= 15 veri
  · IL NUMERO CHE DECIDE PRIMA DI TUTTO: l'AUROC di FactCG RISTRETTO alla
    sotto-popolazione che il nostro moat mette sotto soglia. Se e' ~0,5, li'
    FactCG non discrimina e la cascata e' inutile PER COSTRUZIONE — e allora il
    67,2% dei 61 e' solo il segno che FactCG e' piu' permissivo, non piu' bravo.
    QUESTO controllo va guardato per primo: senza, il resto e' rumore.
"""
import io
import json

S = ("docs/stato-reale/banchi/")
pu = {json.loads(x)["i"]: json.loads(x)
      for x in io.open(S + "_ws4_punteggi_heldout.jsonl", encoding="utf-8") if x.strip()}
fa = {json.loads(x)["i"]: json.loads(x)
      for x in io.open(S + "_ws4_factcg_heldout.jsonl", encoding="utf-8") if x.strip()}
for i in pu:
    pu[i]["nostro"] = (pu[i].get("score") or 0.0) / 100.0
    pu[i]["altro"] = fa[i]["p"][1]

veri = [i for i in pu if pu[i]["label"] == 1]
falsi = [i for i in pu if pu[i]["label"] == 0]


def auroc(ids):
    v = [i for i in ids if pu[i]["label"] == 1]
    f = [i for i in ids if pu[i]["label"] == 0]
    if not v or not f:
        return None, len(v), len(f)
    c = (sum(1 for a in v for b in f if pu[a]["altro"] > pu[b]["altro"])
         + 0.5 * sum(1 for a in v for b in f if pu[a]["altro"] == pu[b]["altro"]))
    return c / (len(v) * len(f)), len(v), len(f)


# ── IL CONTROLLO CHE VA GUARDATO PER PRIMO ──────────────────────────────
print("  == FactCG DISCRIMINA sulla popolazione che noi buttiamo? ==")
print(f"  {'soglia nostra':>14} {'sotto':>7} {'veri':>5} {'falsi':>6} {'AUROC di FactCG li':>20}")
for s in (0.05, 0.10, 0.20, 0.40, 0.80):
    sotto = [i for i in pu if pu[i]["nostro"] < s]
    a, nv, nf = auroc(sotto)
    print(f"  {s:>14.2f} {len(sotto):>7} {nv:>5} {nf:>6}"
          f" {('%.3f' % a) if a is not None else '   —':>20}")
a_tutti, _, _ = auroc(list(pu))
print(f"  {'(tutti i 600)':>14} {len(pu):>7} {len(veri):>5} {len(falsi):>6}"
      f" {a_tutti:>20.3f}")

# ── LA CASCATA, a PARI veri persi ───────────────────────────────────────
BERSAGLIO = 88
ord_n = sorted(veri, key=lambda i: pu[i]["nostro"])
s_nostro = pu[ord_n[BERSAGLIO - 1]]["nostro"] + 1e-12
base_ff = sum(1 for i in falsi if pu[i]["nostro"] < s_nostro)
i61 = [i for i in veri if (pu[i].get("score") or 0) < 5 and pu[i].get("fermato")]
print(f"\n  base: soglia nostra {s_nostro:.4f} · veri persi {BERSAGLIO}"
      f" · falsi fermati {base_ff}/300 = {100*base_ff/300:.1f}%")

print(f"\n  == LA CASCATA (sotto S decide FactCG, con la sua soglia T) ==")
print(f"  {'S':>6} {'T':>6} {'veri persi':>12} {'falsi fermati':>14} {'dei 61 recuperati':>18}")
migliore = None
for S_ in (0.05, 0.10, 0.20, 0.40):
    for T in (0.5, 0.6, 0.7, 0.8, 0.9):
        vp, ff = 0, 0
        for i in veri:
            fermato = (pu[i]["altro"] < T) if pu[i]["nostro"] < S_ else (pu[i]["nostro"] < s_nostro)
            vp += fermato
        for i in falsi:
            fermato = (pu[i]["altro"] < T) if pu[i]["nostro"] < S_ else (pu[i]["nostro"] < s_nostro)
            ff += fermato
        rec = sum(1 for i in i61 if pu[i]["nostro"] < S_ and pu[i]["altro"] >= T)
        if vp <= BERSAGLIO:      # solo le configurazioni che NON perdono piu' veri
            print(f"  {S_:>6.2f} {T:>6.2f} {vp:>5}/300 {100*vp/300:>5.1f}%"
                  f" {ff:>5}/300 {100*ff/300:>5.1f}% {rec:>13}/61")
            if migliore is None or (ff, -rec) > (migliore[2], -migliore[3]):
                migliore = (S_, T, ff, rec, vp)

print("\n  == IL VERDETTO, col vincolo nel codice ==")
if migliore is None:
    print("    nessuna configurazione resta entro gli 88 veri persi")
else:
    S_, T, ff, rec, vp = migliore
    print(f"    la migliore: S={S_:.2f} T={T:.2f} → veri persi {vp}"
          f" · falsi fermati {ff}/300 = {100*ff/300:.1f}% · recuperati {rec}/61")
    tiene = ff >= base_ff and rec >= 15
    print(f"    PREDIZIONE MIA («paga sui falsi»): "
          f"{'FALSIFICATA' if tiene else 'REGGE'}")
    print(f"    ⇒ la cascata {'FUNZIONA' if tiene else 'NON funziona'}:"
          f" {100*ff/300:.1f}% contro il {100*base_ff/300:.1f}% di base,"
          f" {rec} veri recuperati")
