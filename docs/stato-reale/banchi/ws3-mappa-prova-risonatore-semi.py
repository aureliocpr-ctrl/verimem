"""Il controllo sul reperto: `recall_tuple` ha reso `(5, 2, 7)` per una memoria
che conteneva `(1, 2, 3)`, con `ok: True` **e** `converged: True`. La versione
multi-restart trova la tupla giusta e porta anche `residual: 0.0`.

I punti fissi spuri sono attesi in un resonator network (Frady 2020): la
domanda della mappa non è «sbaglia?» ma **«chi lo chiama può accorgersene?»**.
Qui misuro (a) quante volte su dieci semi la fattorizzazione singola azzecca,
(b) quali campi ha la ricevuta nei due casi, (c) se `residual` compare quando
serve.
"""
from __future__ import annotations

import pathlib
import sys

WT = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(WT))
from verimem import resonator_memory as RS  # noqa: E402

rm = RS.ResonatorMemory(n_roles=3, atoms_per_role=8, d=1024, seed=7)
rm.remember_tuple((1, 2, 3))
print("memoria: una sola tupla, (1, 2, 3)\n")

giusti = 0
for seme in range(10):
    r = rm.recall_tuple(n_iter=100, seed=seme)
    ind = r.get("indices")
    ok = ind == (1, 2, 3)
    giusti += ok
    print(f"  seme {seme}: indices={ind} converged={r.get('converged')} "
          f"ok={r.get('ok')} · GIUSTA: {ok}")
print(f"\n>>> fattorizzazioni giuste: {giusti}/10")
print(">>> campi della ricevuta di recall_tuple      :", sorted(rm.recall_tuple(seed=0)))
print(">>> campi della ricevuta di multi_restart     :",
      sorted(rm.recall_tuple_multi_restart(n_restarts=5, n_iter=100)))
print("\nil campo che distingue una soluzione buona da una spuria e' `residual`:")
print("  presente in recall_tuple            :", "residual" in rm.recall_tuple(seed=0))
print("  presente in recall_tuple_multi_restart:",
      "residual" in rm.recall_tuple_multi_restart(n_restarts=3, n_iter=100))
print("\nresiduo VERO delle due risposte (calcolato a mano con _residual_norm):")
r_sbagliata = rm.recall_tuple(n_iter=100, seed=1)
ind_s = r_sbagliata.get("indices")
print(f"  la risposta del seme 1 {ind_s} ->",
      round(float(RS._residual_norm(rm.aggregate, ind_s, rm.codebooks)), 4))
print("  la tupla vera (1, 2, 3)      ->",
      round(float(RS._residual_norm(rm.aggregate, (1, 2, 3), rm.codebooks)), 4))
print("\ne `target_indices` (l'argomento che permette di dire cosa si cercava):")
con_bersaglio = rm.recall_tuple_multi_restart(n_restarts=5, n_iter=100,
                                              target_indices=(1, 2, 3))
print("  con target_indices=(1,2,3):",
      {k: v for k, v in con_bersaglio.items() if k in
       ("indices", "found_match", "residual", "restart")})
