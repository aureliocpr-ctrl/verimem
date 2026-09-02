# -*- coding: utf-8 -*-
"""L'ENSEMBLE nostro+FactCG — il secondo braccio del disegno di @ws3 con un modello
diverso, offline sui punteggi gia' in casa (zero inferenza, zero RAM).

PERCHE' NON E' UN DOPPIONE. @ws3 ha misurato nostro+MiniCheck (87,3/72,0 a
iso-recall) e il lead ha deciso l'ensemble su quel numero. Un solo modello non
dice se il guadagno viene dall'ENSEMBLE o da MiniCheck: se anche un giudice
NETTAMENTE peggiore (FactCG: 66,3% contro 86,7%) aggiunge, allora la
complementarita' e' del metodo; se non aggiunge, il guadagno e' di MiniCheck e
va attribuito a lui.

🔮 PREDIZIONE, scritta PRIMA di eseguire (02/09 20:58):
  · a pari veri persi (88/300) l'ensemble nostro+FactCG ferma fra l'86% e il 90%
    dei falsi — cioe' guadagno PICCOLO o NULLO sul nostro 86,7%, perche' la media
    semplice pesa uguale un giudice molto piu' debole
  · FALSIFICATA se sotto l'84% o sopra il 90%
  · IL CONTROLLO CHE SEPARA DUE SPIEGAZIONI: se l'ensemble vale, deve CAMBIARE
    l'identita' dei veri persi — recuperare una parte dei 61 che il nostro moat
    mette sul fondo. Se ferma esattamente gli stessi, il numero e' rumore.
"""
import io
import json

S = ("docs/stato-reale/banchi/")
pu = {json.loads(x)["i"]: json.loads(x)
      for x in io.open(S + "_ws4_punteggi_heldout.jsonl", encoding="utf-8") if x.strip()}
fa = {json.loads(x)["i"]: json.loads(x)
      for x in io.open(S + "_ws4_factcg_heldout.jsonl", encoding="utf-8") if x.strip()}

for i in pu:
    pu[i]["nostro"] = (pu[i].get("score") or 0.0) / 100.0   # 0-100 -> 0-1
    pu[i]["altro"] = fa[i]["p"][1]
    pu[i]["media"] = (pu[i]["nostro"] + pu[i]["altro"]) / 2.0

veri = [i for i in pu if pu[i]["label"] == 1]
falsi = [i for i in pu if pu[i]["label"] == 0]
BERSAGLIO = 88


def iso(campo):
    """A pari veri persi: quanti falsi ferma."""
    ordinati = sorted(veri, key=lambda i: pu[i][campo])
    s = pu[ordinati[BERSAGLIO - 1]][campo] + 1e-12
    persi = {i for i in veri if pu[i][campo] < s}
    return sum(1 for i in falsi if pu[i][campo] < s), persi, s


print(f"  veri {len(veri)} · falsi {len(falsi)} · bersaglio {BERSAGLIO} veri persi")
print(f"\n  {'giudice':<22} {'falsi fermati':>16}")
esiti = {}
for nome, campo in (("il nostro moat", "nostro"), ("FactCG", "altro"),
                    ("ENSEMBLE media", "media")):
    ff, persi, s = iso(campo)
    esiti[campo] = (ff, persi, s)
    print(f"  {nome:<22} {ff:>4}/300 = {100*ff/300:>5.1f}%   (soglia {s:.4f})")

ff_e = esiti["media"][0]
pe = 100 * ff_e / 300
print(f"\n  ensemble contro il nostro da solo: {pe - 86.7:+.1f} punti"
      f"   [@ws3 con MiniCheck: 87,3%, cioe' +0,6]")
print(f"  PREDIZIONE MIA (86-90%): {'REGGE' if 86 <= pe <= 90 else 'FALSIFICATA'}"
      f"  ({pe:.1f}%)")

# ── IL CONTROLLO CHE SEPARA: cambia l'IDENTITA' dei veri persi? ──────────
p_nostro = esiti["nostro"][1]
p_ens = esiti["media"][1]
recuperati = p_nostro - p_ens
nuovi = p_ens - p_nostro
print("\n  == CAMBIA L'IDENTITA' DEI VERI PERSI? ==")
print(f"    persi da entrambi: {len(p_nostro & p_ens)}"
      f" · recuperati dall'ensemble: {len(recuperati)}"
      f" · persi NUOVI: {len(nuovi)}")
if len(recuperati) == 0:
    print("    => nessuno recuperato: l'ensemble ferma gli STESSI, il numero e' rumore")
else:
    print(f"    => l'ensemble scambia {len(recuperati)} casi con {len(nuovi)}:"
          " la complementarita' esiste")

# ── E I 61 SUL FONDO, che il lead vuole dichiarare INFONDABILI ──────────
i61 = [i for i in veri if (pu[i].get("score") or 0) < 5 and pu[i].get("fermato")]
fond_altro = [i for i in i61 if pu[i]["altro"] >= esiti["altro"][2]]
fond_ens = [i for i in i61 if pu[i]["media"] >= esiti["media"][2]]
print("\n  == I 61 VERI SUL FONDO (score <5, fermati dal nostro moat) ==")
print(f"    li fonda FactCG alla sua iso-recall:  {len(fond_altro)}/{len(i61)}"
      f" = {100*len(fond_altro)/len(i61):.1f}%")
print(f"    li fonda l'ENSEMBLE:                  {len(fond_ens)}/{len(i61)}"
      f" = {100*len(fond_ens)/len(i61):.1f}%")
print("    ⇒ la frase «questi fatti nessun giudice locale li fonda» e'"
      f" {'VERA' if len(fond_altro) == 0 else 'FALSA'}")
