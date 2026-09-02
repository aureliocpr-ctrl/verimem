"""Anello ③ di M1 — T1.2 (soglia per dominio) e T1.4 (terzo stato) OFFLINE.

Nessun carico del giudice: lavora sul dump `punteggi_heldout.jsonl` prodotto il
02/09 alle 11:49Z sul commit eaf32209, con giudice CARICATO (judge_state=ready
dopo 24,3s) e due controlli accesi: 260/300 falsi fermati (86,7%) e 0/600 claim
senza grounding_score. Il dump riproduce la baseline: 88/300 veri fermati.

PREDIZIONI SCRITTE PRIMA (canale, 02/09 10:38Z e 12:0x):
  · T1.2 — lead: >=5 punti di veri persi recuperati a falsita' invariata,
           falsificata se <2.   IO: <2 punti (falsificherei la sua).
  · T1.4 — IO: >=60% dei veri persi DAL MOAT ha score fra 20 e 40 (addossati al
           cut). Falsificata se <40%. Se regge, un terzo stato li recupera; se
           cade, il moat non li sta «quasi ammettendo» e nessuna soglia li salva.

TETTO TEORICO DI T1.2, da dire prima di leggere i numeri: la soglia agisce solo
sul moat. Dei ; veri persi, quelli del moat sono il sottoinsieme con score sotto
il cut; gli altri cadono per layer lessicali e NESSUNA soglia li recupera.

CONTROLLO CHE DEVE ACCENDERSI: applicando la soglia GLOBALE 40 al dump devo
riottenere circa i numeri della baseline. Se non li riottengo, il dump non
rappresenta il gate e i numeri sotto non valgono.
"""
import io
import json
import sys
from collections import defaultdict

CUT = 40.0
D = "punteggi_heldout.jsonl"

righe = [json.loads(x) for x in io.open(D, encoding="utf-8") if x.strip()]
righe = [r for r in righe if r.get("score") is not None]
veri = [r for r in righe if r["label"] == 1]
falsi = [r for r in righe if r["label"] == 0]
print(f"  dump: {len(righe)} righe con punteggio   veri {len(veri)}  falsi {len(falsi)}")

# ── CONTROLLO: la soglia globale riproduce la baseline? ────────────────────
vp_glob = [r for r in veri if r["score"] < CUT]
fa_glob = [r for r in falsi if r["score"] >= CUT]
print(f"\n  CONTROLLO — soglia globale {CUT}:")
print(f"    veri sotto il cut (persi dal MOAT)  {len(vp_glob)}/300"
      f"  ({100*len(vp_glob)/len(veri):.1f}%)")
print(f"    falsi sopra il cut (ammessi)        {len(fa_glob)}/300"
      f"  ({100*len(fa_glob)/len(falsi):.1f}%)")
print("    (baseline dal banco: 88/300 veri fermati IN TOTALE — moat + lessicali;")
print("     qui si vede la sola parte del MOAT, che e' il bersaglio di T1.2/T1.4)")

# ── T1.4 — la mia predizione: dove stanno i punteggi dei veri persi? ───────
print("\n  == T1.4 — DOVE STANNO I PUNTEGGI DEI VERI PERSI DAL MOAT ==")
bande = [(0, 5), (5, 10), (10, 20), (20, 30), (30, 40)]
for lo, hi in bande:
    n = sum(1 for r in vp_glob if lo <= r["score"] < hi)
    q = 100 * n / len(vp_glob) if vp_glob else 0
    print(f"    score {lo:>2}-{hi:<3}  {n:>3}  ({q:5.1f}%)  {'#' * int(q / 2)}")
vicini = sum(1 for r in vp_glob if 20 <= r["score"] < 40)
q_vic = 100 * vicini / len(vp_glob) if vp_glob else 0
print(f"\n    fra 20 e 40 (addossati al cut): {vicini}/{len(vp_glob)} = {q_vic:.1f}%")
print(f"    PREDIZIONE MIA: >=60% regge · <40% falsificata"
      f"  =>  {'REGGE' if q_vic >= 60 else 'FALSIFICATA' if q_vic < 40 else 'INDECISA'}")

# ── T1.2 — soglia per dominio, metà/metà ──────────────────────────────────
print("\n  == T1.2 — SOGLIA PER DOMINIO (strato = category di TruthfulQA) ==")
per_cat = defaultdict(list)
for r in righe:
    per_cat[r.get("category") or "(vuota)"].append(r)
grandi = {k: v for k, v in per_cat.items() if len(v) >= 40}
print(f"    categorie totali {len(per_cat)} · con >=40 righe {len(grandi)}"
      f" ({sum(len(v) for v in grandi.values())} righe)")

def meta(lst):
    """Split deterministico STRATIFICATO PER LABEL.

    Il primo tentativo divideva per indice pari/dispari e dava 0 veri in una
    meta': nel file i claim sono in COPPIE (vero, falso) consecutive, quindi
    pari = tutti veri e dispari = tutti falsi. Il banco non misurava niente e il
    sintomo era leggibile — «veri persi B: 0/0» e «falsi ammessi 40/40».
    Qui veri e falsi si dividono SEPARATAMENTE, cosi' entrambe le meta' hanno
    le due popolazioni."""
    v = sorted((r for r in lst if r["label"] == 1), key=lambda r: r["i"])
    f = sorted((r for r in lst if r["label"] == 0), key=lambda r: r["i"])
    return v[0::2] + f[0::2], v[1::2] + f[1::2]

def valuta(campione, cut):
    vp = sum(1 for r in campione if r["label"] == 1 and r["score"] < cut)
    fa = sum(1 for r in campione if r["label"] == 0 and r["score"] >= cut)
    nv = sum(1 for r in campione if r["label"] == 1)
    nf = sum(1 for r in campione if r["label"] == 0)
    return vp, nv, fa, nf

tot_vp_glob = tot_vp_str = tot_nv = tot_fa_glob = tot_fa_str = tot_nf = 0
print(f"\n    {'categoria':<24} {'n':>4} {'soglia':>7}  {'veri persi B':>14}  {'falsi ammessi B':>16}")
for cat, lst in sorted(grandi.items(), key=lambda kv: -len(kv[1])):
    A, B = meta(lst)
    _, _, fa_glob_A, _ = valuta(A, CUT)
    migliore, best = CUT, None
    for c10 in range(0, 1001):
        c = c10 / 10.0
        vp, nv, fa, nf = valuta(A, c)
        if fa <= fa_glob_A and (best is None or vp < best):
            best, migliore = vp, c
    vpB_s, nvB, faB_s, nfB = valuta(B, migliore)
    vpB_g, _, faB_g, _ = valuta(B, CUT)
    tot_vp_str += vpB_s; tot_vp_glob += vpB_g; tot_nv += nvB
    tot_fa_str += faB_s; tot_fa_glob += faB_g; tot_nf += nfB
    print(f"    {cat[:23]:<24} {len(lst):>4} {migliore:>7.1f}"
          f"  {vpB_s:>3}/{nvB:<3} (glob {vpB_g:>2})"
          f"  {faB_s:>3}/{nfB:<3} (glob {faB_g:>2})")

if tot_nv:
    p_str = 100 * tot_vp_str / tot_nv
    p_glob = 100 * tot_vp_glob / tot_nv
    f_str = 100 * tot_fa_str / tot_nf
    f_glob = 100 * tot_fa_glob / tot_nf
    print(f"\n    TOTALE sulla meta' di MISURA ({tot_nv} veri, {tot_nf} falsi):")
    print(f"      veri persi   soglia globale {p_glob:5.1f}%   per dominio {p_str:5.1f}%"
          f"   => recuperati {p_glob - p_str:+.1f} punti")
    print(f"      falsi ammessi soglia globale {f_glob:5.1f}%   per dominio {f_str:5.1f}%"
          f"   => {f_str - f_glob:+.1f} punti")
    d = p_glob - p_str
    costo = f_str - f_glob
    # IL VINCOLO E' PARTE DELLA PREDIZIONE: «>=5 punti recuperati A FALSITA'
    # INVARIATA». La prima versione di questo banco guardava solo i veri e
    # stampava CONFERMATA mentre i falsi ammessi salivano di 10,9 punti: un
    # verdetto che ignora il vincolo che la predizione contiene.
    invariata = costo <= 1.0
    print(f"\n    vincolo «falsita' invariata»: costo {costo:+.1f} punti"
          f"  =>  {'RISPETTATO' if invariata else 'VIOLATO'}")
    if not invariata:
        esito = "FALSIFICATA (il beneficio c'e', il vincolo NO)"
    elif d >= 5:
        esito = "CONFERMATA"
    elif d < 2:
        esito = "FALSIFICATA"
    else:
        esito = "INDECISA"
    print(f"    PREDIZIONE LEAD (>=5 punti A FALSITA' INVARIATA)  =>  {esito}")
    print(f"    PREDIZIONE MIA (<2 punti recuperati): "
          f"{'REGGE' if d < 2 else 'FALSIFICATA'} — sbagliavo sul beneficio")
    if d > 0 and costo > 0:
        print(f"\n    LO SCAMBIO REALE: {d:.1f} punti di veri salvati per"
              f" {costo:.1f} punti di falsi ammessi = 1 vero ogni"
              f" {costo / d:.1f} falsi.")
sys.exit(0)
